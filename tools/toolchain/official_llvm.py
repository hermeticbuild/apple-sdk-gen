#!/usr/bin/env python3
"""Prepare or verify the pinned official LLVM for Darwin interface generation."""

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.toolchain import llvm_smoke


PIN = Path(__file__).resolve().parent / "data/llvm-official-macos-arm64.json"
TRUSTED_ROOT = "github-attestation-trusted-root.jsonl"


def read_lock(path):
    def unique_object(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError(f"duplicate field in LLVM tool lock: {path}")
        return result

    def fields(record, names):
        if not isinstance(record, dict) or record.keys() != set(names.split()):
            raise ValueError(f"expected fields {names} in LLVM tool lock: {path}")

    lock = json.loads(path.read_text(), object_pairs_hook=unique_object)
    fields(lock, "schema host repository version tag commit archive attestation files symlinks "
           "resource_headers target_architectures minimum_deployment tbd_version darwin_builtins")
    fields(lock["archive"], "url sha256 directory")
    fields(lock["attestation"], "url sha256 signer_workflow")
    fields(lock["resource_headers"], "path count sha256")
    fields(lock["darwin_builtins"], "path architectures")
    files = lock["files"]
    symlinks = lock["symlinks"]
    if not isinstance(files, dict) or not isinstance(symlinks, dict):
        raise ValueError(f"invalid projection inventories in LLVM tool lock: {path}")
    root = lock["archive"]["directory"]
    relative_paths = [*files, *symlinks, lock["resource_headers"]["path"], root]
    digests = [*files.values(), *(lock[key]["sha256"] for key in
                                  ("archive", "attestation", "resource_headers"))]
    if (not all(isinstance(relative, str) and re.fullmatch(r"[\w./-]+", relative) and
                all(part not in ("", ".", "..") for part in relative.split("/"))
                for relative in relative_paths) or
            not all(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
                    for digest in digests) or
            "/" in root or lock["darwin_builtins"]["path"] not in files or
            any(not isinstance(dest, str) or "/" in dest or
                str(Path(link).parent / dest) not in files for link, dest in symlinks.items()) or
            set(files) & set(symlinks)):
        raise ValueError(f"invalid projection path or digest in LLVM tool lock: {path}")
    return lock


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
    resource = Path(lock["resource_headers"]["path"])
    directories = {
        parent for relative in (*files, *symlinks, str(resource))
        for parent in Path(relative).parents
    } | {resource}
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

    headers = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if str(relative) in files or str(relative) in symlinks or relative in directories:
            continue
        if resource not in relative.parents:
            raise ValueError(f"unexpected file or directory in LLVM projection: {path}")
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            headers[str(relative.relative_to(resource))] = sha256(path)
        elif not stat.S_ISDIR(mode):
            raise ValueError(f"unexpected resource entry: {path}")
    tree = json.dumps(headers, sort_keys=True, separators=(",", ":")).encode()
    if (len(headers) != lock["resource_headers"]["count"] or
            hashlib.sha256(tree).hexdigest() != lock["resource_headers"]["sha256"]):
        raise ValueError(f"resource header inventory differs from pin: {root / resource}")


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


def prepare(cache, lock, offline):
    name = lock["archive"]["directory"]
    root = cache / name
    if root.exists() or root.is_symlink():
        projection(root, lock)
        return root
    cache.mkdir(parents=True, exist_ok=True)
    inputs = []
    for asset in (lock["archive"], lock["attestation"]):
        path = cache / asset["url"].rsplit("/", 1)[-1]
        inputs.append(get_cached(path, lambda p: download(asset["url"], p), offline,
                                 asset["sha256"]))
    archive, bundle = inputs
    trusted_root = get_cached(cache / TRUSTED_ROOT, fetch_trusted_root, offline)
    run(["gh", "attestation", "verify", archive, "--bundle", bundle,
         "--custom-trusted-root", trusted_root, "--repo", lock["repository"],
         "--signer-workflow", lock["attestation"]["signer_workflow"],
         "--source-ref", f"refs/tags/{lock['tag']}", "--source-digest", lock["commit"],
         "--deny-self-hosted-runners"])

    members = [*lock["files"], *lock["symlinks"], lock["resource_headers"]["path"]]
    with tempfile.TemporaryDirectory(dir=cache, prefix=".extract-") as tmp:
        with subprocess.Popen(["zstd", "--long=30", "--decompress", "--stdout", archive],
                              stdout=subprocess.PIPE) as decoder:
            try:
                run(["/usr/bin/tar", "-xf", "-", "-C", tmp,
                     *(f"{name}/{member}" for member in members)], stdin=decoder.stdout)
            finally:
                decoder.stdout.close()
            if decoder.wait():
                raise ValueError(f"zstd could not decode pinned archive: {archive}")
        staged = Path(tmp) / name
        projection(staged, lock)
        try:
            staged.rename(root)
        except OSError:
            if not root.is_dir():
                raise
            projection(root, lock)
    return root


def write_receipt(path, receipt):
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".receipt-") as tmp:
        staged = Path(tmp) / path.name
        staged.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        os.replace(staged, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    cache_parser = commands.add_parser("prepare", help="verify and prepare the release projection")
    cache_parser.add_argument("--cache", type=Path, required=True)
    cache_parser.add_argument("--offline", action="store_true")
    verify_parser = commands.add_parser("verify", help="rehash and probe an existing projection")
    verify_parser.add_argument("--llvm-dir", type=Path, required=True)
    for command in (cache_parser, verify_parser):
        command.add_argument("--c-install", type=Path, help="run a smoke test with generated C headers")
        command.add_argument("--receipt", type=Path, help="write portable verification JSON")
        command.add_argument("--work-dir", type=Path, help="keep fixtures in a new child of this directory")
    args = parser.parse_args()
    try:
        lock = read_lock(PIN)
        host = f"{platform.system().lower()}-{platform.machine().lower()}"
        if lock["schema"] != 1 or lock["tbd_version"] != 5 or lock["host"] != host:
            raise ValueError(f"no supported official LLVM lock for {host}")
        if args.command == "prepare":
            root = prepare(args.cache.resolve(), lock, args.offline)
        else:
            root = args.llvm_dir.absolute()
            projection(root, lock)
            root = root.resolve()
        if args.work_dir:
            work = Path(tempfile.mkdtemp(prefix="llvm-smoke-", dir=args.work_dir.resolve()))
            print(f"LLVM smoke files: {work}", file=sys.stderr)
            capabilities = llvm_smoke.verify(root, work, args.c_install, lock, run, sha256)
        else:
            with tempfile.TemporaryDirectory(prefix="llvm-smoke-") as tmp:
                capabilities = llvm_smoke.verify(root, Path(tmp).resolve(), args.c_install,
                                                 lock, run, sha256)
        if args.receipt:
            write_receipt(args.receipt, {
                "schema": 1,
                "lock_sha256": sha256(PIN),
                "macos_version": platform.mac_ver()[0],
                "release": lock,
                "capabilities": capabilities,
            })
        print(root)
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"{error}\n{error.stderr or error.stdout or ''}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
