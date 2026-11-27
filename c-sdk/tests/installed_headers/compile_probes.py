#!/usr/bin/env python3
"""Compile the checked-in default C probe with only Clang and its C package."""

import argparse
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


COMBINED = HERE / "default_profile.c"
COMPILER_ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clang", required=True, type=Path)
    parser.add_argument("--sysroot", required=True, type=Path)
    parser.add_argument("--fixture", action="append", default=[], type=Path,
                        help="additional C translation unit to compile on arm64")
    args = parser.parse_args()
    sysroot = args.sysroot.resolve()
    roots = re.findall(r"^#include <([^>]+)>", COMBINED.read_text(), re.MULTILINE)
    if not roots or len(roots) != len(set(roots)):
        parser.error("C fixture must contain unique include roots")
    resource = subprocess.check_output(
        [str(args.clang), "--no-default-config", "-print-resource-dir"],
        text=True, env=COMPILER_ENV).strip()
    failures = []
    base = [str(args.clang), "--no-default-config", "-target", "arm64-apple-macos14.0",
            "-isysroot", str(sysroot), "-nostdinc",
            "-isystem", resource + "/include",
            "-isystem", str(sysroot / "usr/include"),
            "-std=c11", "-fsyntax-only", "-x", "c"]
    for name in roots:
        flags = ["-D_XOPEN_SOURCE=700"] if name == "ucontext.h" else []
        result = subprocess.run([*base, *flags, "-"],
                                input=f"#include <{name}>\n",
                                text=True, capture_output=True, env=COMPILER_ENV)
        if result.returncode:
            failures.append((name, result.stderr.splitlines()[-3:]))
    for fixture in (COMBINED, *args.fixture):
        result = subprocess.run([*base, str(fixture.resolve())],
                                text=True, capture_output=True, env=COMPILER_ENV)
        if result.returncode:
            failures.append((fixture, result.stderr.splitlines()[-3:]))
    total = len(roots) + 1 + len(args.fixture)
    print(f"{total - len(failures)}/{total} C compilation checks passed")
    for name, lines in failures:
        print(f"FAIL arm64 {name}: {'; '.join(lines)}")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
