"""Write source receipts and license notices into the minimal macOS SDK."""

import argparse
import json
from pathlib import Path
import subprocess

from components.simd import generate_headers as simd
from tools.fetch_sources import read_lock
from tools.read_header_manifest import read_header_manifest
from tools.sdk_composition.compose_sdk import SYSTEM_COMPAT_NAMES, digest, relative_path


REPO = Path(__file__).resolve().parents[2]
PROVENANCE = "c-sdk-provenance.json"
STUBS = {
    "libSystem.B": "tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.md",
    **{f"lib{name}": "tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.md"
       for name in ("System", *SYSTEM_COMPAT_NAMES)},
    **{f"lib{name}": "tools/apple_sdk_gen/supplements/generate_system_library_stubs.py (iOS SDK export data)"
       for name in ("z", "z.1", "bsm", "bsm.0", "ipsec", "ipsec.A")},
    **{f"lib{name}": "components/libiconv/generate_stubs.py (Apple OSS InstallAPI)"
       for name in ("iconv", "iconv.2", "charset", "charset.1")},
    **{f"lib{name}": "components/libresolv/stubs.md (Apple OSS InstallAPI)"
       for name in ("resolv", "resolv.9")},
}


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


def write_provenance(sdk, sources, lock_path):
    lock, projects = read_lock(lock_path)
    check_header_inputs(sdk, sources, projects)
    additional = {}

    def install(name, contents, origin):
        file = sdk / name
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("xb") as stream:
            stream.write(contents)
        additional[name] = {"sha256": digest(file), "source": origin}

    install("source-lock.json", lock, lock_path.relative_to(REPO).as_posix())
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
    snapshot = json.loads(lock)["docc"]
    simd_generator = Path(simd.__file__).resolve()
    data = {
        "source_commit": revision,
        "additional_files": additional,
        "simd": {
            "snapshot_sha256": snapshot["sha256"],
            "generator": simd_generator.relative_to(REPO).as_posix(),
            "generator_sha256": digest(simd_generator),
            "pages": [f"https://developer.apple.com/documentation/simd/{page}" for page in simd.docc_pages()],
        },
        "linker_stubs": {f"usr/lib/{name}.tbd": origin for name, origin in STUBS.items()},
    }
    (sdk / PROVENANCE).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("c_sdk", type=Path)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    args = parser.parse_args()
    try:
        write_provenance(args.c_sdk.resolve(), args.sources.resolve(), args.lock.resolve())
    except (OSError, ValueError, KeyError) as err:
        parser.exit(1, f"C SDK: {err}\n")


if __name__ == "__main__":
    main()
