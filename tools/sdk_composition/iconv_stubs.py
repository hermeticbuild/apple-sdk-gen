"""Generate the macOS libiconv and libcharset link stubs from Apple's OSS project."""

import argparse
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

from tools.sdk_composition.compose_sdk import Plan, c_install, digest
from tools.toolchain import official_llvm


REVISION = "7fb0198429570d3b6aa562d228a6ea5936d15c05"
PROJECT = "libiconv.xcodeproj/project.pbxproj"


def build_stub(target_name, project, src, sysroot, llvm, lock, work, libdir):
    target = next(t for t in project.values() if t["isa"] == "PBXNativeTarget"
                  and t["name"] == target_name)
    configs = project[target["buildConfigurationList"]]["buildConfigurations"]
    settings = next(project[k]["buildSettings"] for k in configs
                    if project[k]["name"] == "Release")
    phase = next(project[k] for k in target["buildPhases"]
                 if project[k]["isa"] == "PBXHeadersBuildPhase")
    paths = []
    for file_id in phase["files"]:
        file = project[file_id]
        ref = file["fileRef"]
        group = next(g for g in project.values() if g["isa"] == "PBXGroup"
                     and ref in g["children"])
        path = Path(group.get("path", "")) / project[ref]["path"]
        paths.append({"path": path.as_posix(), "type": file["settings"]["ATTRIBUTES"][0].lower()})
    listing = work / "headers.json"
    listing.write_text(json.dumps({"version": "3", "headers": [
        {**h, "path": str(src / h["path"])} for h in paths
    ]}))
    dylib = project[target["productReference"]]["path"]
    stub = libdir / Path(dylib).with_suffix(".tbd")
    if target_name == "libiconv":
        # Expand only the non-deployment InstallAPI settings of this pinned project.
        entries = dict(line.split(" = ", 1) for line in
                       (src / "xcodeconfig/libiconv.xcconfig").read_text().splitlines()
                       if line.startswith("OTHER_TAPI_FLAGS"))
        options = entries["OTHER_TAPI_FLAGS"].replace(
            "$(OTHER_TAPI_FLAGS_$(DEPLOYMENT_LOCATION))", entries["OTHER_TAPI_FLAGS_NO"])
        extra = [arg.replace("$(BUILT_PRODUCTS_DIR)", str(libdir)).replace("$(SRCROOT)", str(src))
                 for arg in options.split()]
    else:
        extra = ["-I", src / "libcharset"]
    cmd = [
        llvm / "bin/clang-installapi", "-x", "c", "-nostdinc", "-isysroot", sysroot,
        "-isystem", llvm / lock["resource_headers"]["path"], "-isystem", sysroot / "usr/include",
        "-dynamiclib", "-install_name", "/usr/lib/" + dylib,
        "-current_version", settings["DYLIB_CURRENT_VERSION"],
        "-compatibility_version", settings["DYLIB_COMPATIBILITY_VERSION"],
        "--filetype=tbd-v5", *extra,
    ]
    for arch in lock["target_architectures"]:
        cmd.extend(["-target", f"{arch}-apple-macos{lock['minimum_deployment']}"])
    scan = subprocess.run([*cmd, listing, "-o", stub], cwd=work, env={"LC_ALL": "C"},
                          stderr=subprocess.PIPE, text=True)
    # InstallAPI can emit frontend errors while exiting successfully.
    if scan.returncode or scan.stderr:
        raise ValueError(f"InstallAPI failed for {dylib}: {scan.stderr}")
    alias = libdir / (stub.name.split(".")[0] + ".tbd")
    alias.symlink_to(stub.name)  # xcodescripts/dest_cleanup.sh, ACTION=installapi.
    return stub.name, {"sha256": digest(stub), "headers": paths, "alias": alias.name}


def generate(source, headers, llvm, out):
    if out.exists() or out.is_symlink():
        raise ValueError(f"choose a new output directory: {out}")
    lock = official_llvm.read_lock(official_llvm.PIN)
    official_llvm.projection(llvm, lock)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        work = Path(tmp)
        # Only the pinned commit enters the header search, including quoted includes.
        archive = subprocess.check_output([
            "git", "--no-replace-objects", "-C", source, "archive", REVISION, "citrus", "libcharset", PROJECT,
            "xcodeconfig", "xcodescripts/dest_cleanup.sh",
        ])
        src = work / "src"
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(src, filter="data")
        project = json.loads(subprocess.check_output([
            "/usr/bin/plutil", "-convert", "json", "-o", "-", src / PROJECT,
        ]))["objects"]
        sysroot = work / "sysroot"
        plan = Plan()
        c_install(plan, headers)
        plan.materialize(sysroot)
        stage = work / "output"
        libdir = stage / "usr/lib"
        libdir.mkdir(parents=True)
        results = dict(build_stub(target, project, src, sysroot, llvm, lock, work, libdir)
                       for target in ("charset", "libiconv"))
        manifest = {
            "repository": "https://github.com/apple-oss-distributions/libiconv",
            "revision": REVISION, "project": PROJECT, "llvm_lock_sha256": digest(official_llvm.PIN),
            "c_manifests": {p.name: digest(sysroot / p) for p in plan.files
                            if p.parent == Path(".")},
            "stubs": results,
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        stage.rename(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "c-install", "llvm", "out"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    try:
        generate(args.source.resolve(), args.c_install.resolve(), args.llvm.resolve(), args.out.absolute())
    except (OSError, ValueError, subprocess.CalledProcessError) as err:
        parser.exit(1, f"{err}\n")


if __name__ == "__main__":
    main()
