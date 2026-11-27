#!/usr/bin/env python3
"""Fetch, verify, and unpack the pinned LLVM tools and C++ headers."""

import argparse
import platform
import subprocess
import tempfile
from pathlib import Path

from tools.apple_sdk_gen.supplements.libcxx import fetch_asset, read_llvm_lock, sha256


RECEIPT = ".archive-sha256"


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, **kwargs).stdout


def verify_prepared(root, lock):
    receipt = root / RECEIPT
    if (root.is_symlink() or receipt.is_symlink() or not receipt.is_file()
            or receipt.read_text().strip() != lock["archive"]["sha256"]):
        raise ValueError(f"LLVM directory does not match the pinned archive: {root}. "
                         "Run make prepare-llvm with a fresh LLVM_DIR.")


def prepare(root, cache, lock, offline):
    if root.exists() or root.is_symlink():
        verify_prepared(root, lock)
        return root
    root.parent.mkdir(parents=True, exist_ok=True)
    archive = fetch_asset(cache, lock["archive"], offline)
    name = lock["archive"]["directory"]
    members = [*lock["tools"], lock["resource_headers"], lock["cxx_headers"],
               lock["darwin_builtins"]]
    with tempfile.TemporaryDirectory(dir=root.parent, prefix=".extract-llvm-") as tmp:
        run(["/usr/bin/tar", "-xf", archive, "-C", tmp, *(f"{name}/{member}" for member in members)])
        staged = Path(tmp) / name
        (staged / RECEIPT).write_text(lock["archive"]["sha256"] + "\n")
        try:
            staged.rename(root)
        except OSError:
            if not root.exists():
                raise
            verify_prepared(root, lock)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    try:
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise ValueError("the pinned LLVM tools require arm64 macOS")
        lock = read_llvm_lock()
        print(prepare(args.dest.absolute(), args.cache.resolve(), lock, args.offline))
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"{error}\n{error.stderr or error.stdout or ''}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
