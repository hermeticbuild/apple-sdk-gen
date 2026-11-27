"""Check that the extracted minimal and full macOS SDKs agree on shared files."""

import argparse
import json
from pathlib import Path

from tools.read_header_manifest import read_header_manifest
from tools.sdk_composition.compose_sdk import digest, relative_path
from tools.sdk_composition.write_minimal_sdk_provenance import PROVENANCE, STUBS


SIMD = ("usr/include/simd/simd.h", "usr/include/simd/module.modulemap")
METADATA = {"header-manifest.tsv", "SDKSettings.json"}


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
    parser.add_argument("full_sdk", type=Path)
    args = parser.parse_args()
    try:
        check_archives(args.c_sdk.resolve(), args.full_sdk.resolve())
    except (OSError, ValueError, KeyError) as err:
        parser.exit(1, f"C SDK: {err}\n")


if __name__ == "__main__":
    main()
