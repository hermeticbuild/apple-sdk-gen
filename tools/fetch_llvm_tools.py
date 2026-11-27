#!/usr/bin/env python3
"""Fetch, verify, and unpack the pinned LLVM tools and C++ headers."""

import argparse
import hashlib
import json
import os
import platform
import stat
import subprocess
import tempfile
from pathlib import Path

from tools.apple_sdk_gen.supplements.libcxx import LLVM_PIN as PIN, fetch_archive


TRUSTED_ROOT = "github-attestation-trusted-root.jsonl"


def read_lock(path):
    return json.loads(path.read_text())


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_digest(path, expected):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing regular file: {path}")
    if sha256(path) != expected:
        raise ValueError(f"SHA-256 mismatch: {path}")


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, **kwargs).stdout


def projection(root, lock):
    """Rehash all files, checking link targets and rejecting undeclared inputs."""
    files = lock["files"]
    symlinks = lock["symlinks"]
    trees = {Path(lock[key]["path"]): lock[key] for key in ("resource_headers", "cxx_headers")}
    directories = {
        parent for relative in (*files, *symlinks, *trees)
        for parent in Path(relative).parents
    } | trees.keys()
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"missing prepared LLVM directory: {root}")
    for relative in directories:
        path = root / relative
        if not path.is_dir() or path.is_symlink():
            raise ValueError(f"missing regular directory: {path}")
    for relative, digest in files.items():
        path = root / relative
        check_digest(path, digest)
        if relative.startswith("bin/") and not os.access(path, os.X_OK):
            raise ValueError(f"LLVM tool is not executable: {path}")
    for relative, destination in symlinks.items():
        path = root / relative
        if not path.is_symlink() or os.readlink(path) != destination:
            raise ValueError(f"expected symlink {path} -> {destination}")

    headers = {root: {} for root in trees}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if str(relative) in files or str(relative) in symlinks or relative in directories:
            continue
        for parent in relative.parents:
            if parent in trees:
                break
        else:
            raise ValueError(f"unexpected file or directory in LLVM directory: {relative}")
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            headers[parent][str(relative.relative_to(parent))] = sha256(path)
        elif not stat.S_ISDIR(mode):
            raise ValueError(f"unexpected header entry: {path}")
    for directory, expected in trees.items():
        files = headers[directory]
        tree = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
        if len(files) != expected["count"] or hashlib.sha256(tree).hexdigest() != expected["sha256"]:
            raise ValueError(f"header inventory differs from pin: {root / directory}")


def get_cached(path, command, offline, expected=None):
    if not path.exists():
        if offline:
            raise ValueError(f"offline mode requires cached input: {path}")
        with tempfile.TemporaryDirectory(dir=path.parent, prefix=".download-") as tmp:
            incoming = Path(tmp) / path.name
            command(incoming)
            if expected:
                check_digest(incoming, expected)
            os.replace(incoming, path)
    if expected:
        check_digest(path, expected)
    elif path.is_symlink() or not path.is_file():
        raise ValueError(f"missing regular file: {path}")
    return path


def download(url, destination):
    run(["curl", "--fail", "--location", "--silent", "--show-error", "--retry", "2",
         "--output", destination, url])


def fetch_trusted_root(destination):
    destination.write_text(run(["gh", "attestation", "trusted-root"]))


def prepare(root, cache, lock, offline):
    if root.exists() or root.is_symlink():
        projection(root, lock)
        return root
    root.parent.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    archive = fetch_archive(cache, lock["archive"], offline)
    asset = lock["attestation"]
    bundle = get_cached(cache / asset["url"].rsplit("/", 1)[-1],
                        lambda p: download(asset["url"], p), offline, asset["sha256"])
    trusted_root = get_cached(cache / TRUSTED_ROOT, fetch_trusted_root, offline)
    run(["gh", "attestation", "verify", archive, "--bundle", bundle,
         "--custom-trusted-root", trusted_root, "--repo", lock["repository"],
         "--signer-workflow", asset["signer_workflow"],
         "--source-ref", f"refs/tags/{lock['tag']}", "--source-digest", lock["commit"],
         "--deny-self-hosted-runners"])

    name = lock["archive"]["directory"]
    members = [*lock["files"], *lock["symlinks"], lock["resource_headers"]["path"],
               lock["cxx_headers"]["path"]]
    with tempfile.TemporaryDirectory(dir=root.parent, prefix=".extract-llvm-") as tmp:
        run(["/usr/bin/tar", "-xf", archive, "-C", tmp, *(f"{name}/{member}" for member in members)])
        staged = Path(tmp) / name
        projection(staged, lock)
        try:
            staged.rename(root)
        except OSError:
            if root.is_symlink() or not root.is_dir():
                raise
            projection(root, lock)
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    try:
        lock = read_lock(PIN)
        host = f"{platform.system().lower()}-{platform.machine().lower()}"
        if lock["host"] != host:
            raise ValueError(f"no pinned LLVM tools for {host}")
        print(prepare(args.dest.absolute(), args.cache.resolve(), lock, args.offline))
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"{error}\n{error.stderr or error.stdout or ''}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
