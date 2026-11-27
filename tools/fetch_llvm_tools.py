#!/usr/bin/env python3
"""Fetch, verify, and unpack the pinned LLVM tools and C++ headers."""

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen

RECEIPT = ".archive-sha256"


def read_llvm_lock(path):
    return json.loads(path.read_text())["llvm"]


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch_archive(cache, asset, offline):
    url = asset["url"]
    archive = cache / url.rsplit("/", 1)[-1]
    if archive.is_file() and not archive.is_symlink():
        if sha256(archive) != asset["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {archive}")
        return archive
    if archive.exists() or archive.is_symlink():
        raise ValueError(f"expected a regular file: {archive}")
    if offline:
        raise ValueError(f"offline mode requires cached input: {archive}")
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as tmp:
        incoming = Path(tmp) / archive.name
        with urlopen(url, timeout=120) as response, incoming.open("wb") as output:
            shutil.copyfileobj(response, output)
        if sha256(incoming) != asset["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {incoming}")
        incoming.replace(archive)
    return archive


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
    archive = fetch_archive(cache, lock["archive"], offline)
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
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--dest", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    try:
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise ValueError("the pinned LLVM tools require arm64 macOS")
        lock = read_llvm_lock(args.lock)
        print(prepare(args.dest.absolute(), args.cache.resolve(), lock, args.offline))
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"{error}\n{error.stderr or error.stdout or ''}")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
