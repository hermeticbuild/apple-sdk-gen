#!/usr/bin/env python3
"""Compare standalone C headers with a pristine SDK Gen SDK, read-only."""

import argparse
import json
import subprocess
from pathlib import Path


def headers(root: Path) -> set[str]:
    return {str(path.relative_to(root)) for path in root.rglob("*.h")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--c-root", required=True, type=Path)
    parser.add_argument("--reference-sdk", required=True, type=Path)
    parser.add_argument("--clang", required=True,
                        help="clang from the pinned minimal LLVM prebuilt")
    args = parser.parse_args()
    c_root = args.c_root.resolve()
    base = args.reference_sdk.resolve()
    resource = Path(subprocess.check_output(
        [args.clang, "-print-resource-dir"], text=True).strip()) / "include"

    base_c = {name for name in headers(base / "usr/include")
              if not name.startswith("c++/v1/")}
    own_c = headers(c_root / "usr/include")
    missing = sorted(base_c - own_c)
    resource_provided = [name for name in missing if (resource / name).is_file()]
    unresolved = [name for name in missing if name not in resource_provided]

    base_cf = headers(base / "System/Library/Frameworks/CoreFoundation.framework/Headers")
    own_cf = headers(c_root / "System/Library/Frameworks/CoreFoundation.framework/Headers")
    common_c = base_c & own_c
    identical_c = sorted(name for name in common_c
                         if (base / "usr/include" / name).read_bytes() ==
                         (c_root / "usr/include" / name).read_bytes())
    common_cf = base_cf & own_cf
    identical_cf = sorted(name for name in common_cf
                          if (base / "System/Library/Frameworks/CoreFoundation.framework/Headers" / name).read_bytes() ==
                          (c_root / "System/Library/Frameworks/CoreFoundation.framework/Headers" / name).read_bytes())
    result = {
        "reference_c_header_paths": len(base_c),
        "standalone_c_header_paths": len(own_c),
        "missing_from_standalone": unresolved,
        "provided_by_clang_resource": resource_provided,
        "extra_standalone_paths": sorted(own_c - base_c),
        "common_c_paths": len(common_c),
        "byte_identical_c_paths": identical_c,
        "different_c_paths": sorted(common_c - set(identical_c)),
        "reference_corefoundation_header_paths": len(base_cf),
        "standalone_corefoundation_header_paths": len(own_cf),
        "missing_corefoundation_paths": sorted(base_cf - own_cf),
        "common_corefoundation_paths": len(common_cf),
        "byte_identical_corefoundation_paths": identical_cf,
        "different_corefoundation_paths": sorted(common_cf - set(identical_cf)),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
