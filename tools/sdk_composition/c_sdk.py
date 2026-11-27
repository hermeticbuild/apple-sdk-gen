"""Record C SDK sources and verify the two extracted release archives."""

import argparse
import json
from pathlib import Path
import subprocess

from tools.apple_sdk_gen.supplements import simd
from tools.header_manifest import read_header_manifest
from tools.sdk_composition.compose_sdk import SYSTEM_COMPAT_NAMES, digest, relative_path
from tools.sources.locked_sources import read_lock, verify


REPO = Path(__file__).resolve().parents[2]
PROVENANCE = "c-sdk-provenance.json"
SIMD = ("usr/include/simd/simd.h", "usr/include/simd/module.modulemap")
STUBS = {
    "libSystem.B": "tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.md",
    **{f"lib{name}": "tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.md"
       for name in ("System", *SYSTEM_COMPAT_NAMES)},
    **{f"lib{name}": "tools/apple_sdk_gen/supplements/system_libs.py (iOS SDK export data)"
       for name in ("z", "z.1", "bsm", "bsm.0", "ipsec", "ipsec.A")},
    **{f"lib{name}": "components/libiconv/generate_stubs.py (Apple OSS InstallAPI)"
       for name in ("iconv", "iconv.2", "charset", "charset.1")},
    **{f"lib{name}": "components/libresolv/stubs.md (Apple OSS InstallAPI)"
       for name in ("resolv", "resolv.9")},
}
METADATA = {"header-manifest.tsv", "SDKSettings.json"}


def checked_input(value, sources, projects):
    path = relative_path(value)
    if path.parts[0] == "sources" and len(path.parts) > 2 and path.parts[1] in projects:
        root = sources / path.parts[1]
        file = root.joinpath(*path.parts[2:])
    elif path.parts[0] == "components":
        root = REPO / "components"
        file = REPO / path
    else:
        raise ValueError(f"unsupported header input: {value}")
    if not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"missing or escaped header input: {value}")
    return file


def check_header_inputs(sdk, sources, projects):
    headers, _ = read_header_manifest(sdk)
    for name, row in headers.items():
        origin = row["origin"].removeprefix("derived:")
        inputs = row["inputs"]
        for value in inputs:
            checked_input(value, sources, projects)
        if origin.startswith("generated:"):
            if not any(value.startswith("sources/") for value in inputs):
                raise ValueError(f"missing upstream generator inputs: {name}")
        elif origin not in inputs:
            raise ValueError(f"header origin is missing from inputs: {name}: {origin}")
        if row["transform"] == "copy" and digest(checked_input(origin, sources, projects)) != row["sha256"]:
            raise ValueError(f"header differs from its copy source: {name}")


def write_provenance(sdk, sources):
    lock, projects = read_lock("macosx26.5")
    verify(sources, projects)
    check_header_inputs(sdk, sources, projects)
    additional = {}

    def install(name, contents, origin):
        file = sdk / name
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("xb") as stream:
            stream.write(contents)
        additional[name] = {"sha256": digest(file), "source": origin}

    install("source-lock.json", lock, "locks/macosx26.5.json")
    for project in sorted(projects):
        for name in ("APPLE_LICENSE", "LICENSE"):
            source = sources / project / name
            if source.is_file():
                install(f"usr/share/licenses/{project}/{name}", source.read_bytes(), f"sources/{project}/{name}")
    for path, project in (("components/libm/licenses/APSL-1.1.txt", "APSL-1.1"), ("LICENSE", "apple-sdk-gen")):
        install(f"usr/share/licenses/{project}/LICENSE", (REPO / path).read_bytes(), path)
    unwind = "libunwind/libunwind/LICENSE.TXT"
    install("usr/share/licenses/libunwind/LICENSE.TXT", (sources / unwind).read_bytes(), f"sources/{unwind}")
    install("usr/share/licenses/C-SDK.md", (REPO / "docs/c-sdk-licensing.md").read_bytes(),
            "docs/c-sdk-licensing.md")

    # MIG emits the interfaces without the source comments. Preserve the
    # leading notices of the public .defs and their kernel input when present.
    headers, _ = read_header_manifest(sdk)
    defs = {value for row in headers.values() for value in row["inputs"] if value.endswith(".defs")}
    for value in sorted(defs):
        file = checked_input(value, sources, projects)
        paths = [value]
        kernel = sources / "xnu/osfmk/mach" / file.name
        if kernel.is_file():
            paths.append("sources/" + str(kernel.relative_to(sources)))
        for path in paths:
            body = checked_input(path, sources, projects).read_bytes().lstrip()
            if body.startswith(b"/*") and b"*/" in body:
                notice, _, _ = body.partition(b"*/")
                name = "usr/share/licenses/xnu/" + path.removeprefix("sources/xnu/") + ".txt"
                if name not in additional:
                    install(name, notice + b"*/\n", path)

    revision = subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD"], text=True).strip()
    snapshot = (REPO / "release/docc.snapshot").read_text().split()
    data = {
        "source_commit": revision,
        "additional_files": additional,
        "simd": {
            "snapshot_sha256": snapshot[0],
            "generator": "tools/apple_sdk_gen/supplements/simd.py",
            "generator_sha256": digest(REPO / "tools/apple_sdk_gen/supplements/simd.py"),
            "pages": [f"https://developer.apple.com/documentation/simd/{page}" for page in simd.docc_pages()],
        },
        "linker_stubs": {f"usr/lib/{name}.tbd": origin for name, origin in STUBS.items()},
    }
    (sdk / PROVENANCE).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def check_archives(c_sdk, full_sdk):
    headers, _ = read_header_manifest(c_sdk)
    composition = json.loads((c_sdk / "composition.json").read_text())["files"]
    provenance = json.loads((c_sdk / PROVENANCE).read_text())
    additional = provenance["additional_files"]
    if ("source-lock.json" not in additional or
            any(name != "source-lock.json" and not relative_path(name).is_relative_to("usr/share/licenses")
                for name in additional)):
        raise ValueError("unexpected C SDK provenance assets")
    stubs = {f"usr/lib/{name}.tbd" for name in STUBS}
    shared = set(headers) | set(SIMD) | stubs | METADATA
    if set(composition) != shared or set(provenance["linker_stubs"]) != stubs:
        raise ValueError("C SDK composition differs from its header and stub set")
    expected = shared | set(additional) | {"composition.json", PROVENANCE}
    actual = {str(path.relative_to(c_sdk)) for path in c_sdk.rglob("*")
              if path.is_symlink() or not path.is_dir()}
    directories = {relative_path(name).parent for name in expected}
    allowed_dirs = {ancestor for path in directories for ancestor in (path, *path.parents)}
    if (actual != expected or
            any(path.relative_to(c_sdk) not in allowed_dirs for path in c_sdk.rglob("*") if path.is_dir())):
        raise ValueError(f"unexpected C SDK contents: {sorted(actual ^ expected)}")
    full = json.loads((full_sdk / "composition.json").read_text())["files"]
    for name, row in (composition | additional).items():
        path = c_sdk / relative_path(name)
        if "symlink" in row:
            if not path.is_symlink() or str(path.readlink()) != row["symlink"]:
                raise ValueError(f"C SDK symlink differs from its receipt: {name}")
            if not path.resolve(strict=True).is_relative_to(c_sdk):
                raise ValueError(f"C SDK symlink escapes its tree: {name}")
        elif path.is_symlink() or digest(path) != row["sha256"]:
            raise ValueError(f"C SDK file differs from its receipt: {name}")
        if name in headers and headers[name]["sha256"] != row["sha256"]:
            raise ValueError(f"C SDK header differs from its source receipt: {name}")
        if name in shared:
            peer = full_sdk / name
            if (full.get(name) != row or
                    (peer.is_symlink(), peer.readlink() if peer.is_symlink() else digest(peer)) !=
                    (path.is_symlink(), path.readlink() if path.is_symlink() else row["sha256"])):
                raise ValueError(f"C and full SDKs differ at shared path: {name}")
    print(f"Verified {len(headers)} C headers, {len(SIMD)} SIMD files and {len(stubs)} stubs in both archives.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("c_sdk", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-provenance", metavar="SOURCE_ROOT", type=Path)
    mode.add_argument("--compare", metavar="FULL_SDK", type=Path)
    args = parser.parse_args()
    try:
        if args.write_provenance:
            write_provenance(args.c_sdk.resolve(), args.write_provenance.resolve())
        else:
            check_archives(args.c_sdk.resolve(), args.compare.resolve())
    except (OSError, ValueError, KeyError) as err:
        parser.exit(1, f"C SDK: {err}\n")


if __name__ == "__main__":
    main()
