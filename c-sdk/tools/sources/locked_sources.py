#!/usr/bin/env python3
"""Prepare and verify the selected Apple OSS checkouts for one SDK."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMIT = r"[0-9a-f]{40}"
CHECKOUT_SETTINGS = {
    "core.attributesFile": os.devnull,
    "core.autocrlf": "false",
    "core.eol": "lf",
    "core.symlinks": "true",
    "core.sparseCheckout": "false",
}


def read_lock(sdk: str, profile: str | None = None) -> tuple[bytes, dict]:
    if not re.fullmatch(r"[a-z][a-z0-9]*[0-9](?:\.[0-9]+)+", sdk):
        raise ValueError(f"invalid SDK name: {sdk}")
    if profile not in (None, "objc4"):
        raise ValueError(f"unsupported source profile: {profile}")
    suffix = f"-{profile}" if profile else ""
    path = ROOT / "locks" / f"{sdk}{suffix}.json"
    data = path.read_bytes()
    lock = json.loads(data)
    target = lock["sdk"]
    if lock["schema"] != 1 or target["canonical_name"] != sdk:
        raise ValueError(f"source lock does not identify SDK {sdk}")
    if lock.get("profile") != profile:
        raise ValueError(f"source lock does not identify profile {profile}")
    if target["platform"] != "macosx" or sdk != target["platform"] + target["version"]:
        raise ValueError(f"the header recipes do not support SDK {sdk}")
    projects = lock["projects"]
    if not projects:
        raise ValueError(f"no projects in source lock: {path}")
    for name, pin in projects.items():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
            raise ValueError(f"invalid project name: {name}")
        if not re.fullmatch(COMMIT, pin["commit"]) or not pin["url"].startswith("https://"):
            raise ValueError(f"invalid source pin for {name}")
    return data, projects


def git(directory: Path, *args: str) -> str:
    settings = [option for key, value in CHECKOUT_SETTINGS.items()
                for option in ("-c", f"{key}={value}")]
    return subprocess.check_output(
        ["git", *settings, "-C", str(directory), *args], text=True,
        env=dict(os.environ, GIT_ATTR_NOSYSTEM="1")).strip()


def verify(root: Path, projects: dict) -> None:
    if not root.is_dir():
        raise ValueError(f"missing source tree: {root}; run locked_sources prepare")
    actual = {path.name for path in root.iterdir()}
    if actual != projects.keys():
        raise ValueError(f"source tree differs from lock: missing={sorted(projects.keys() - actual)}, "
                         f"unexpected={sorted(actual - projects.keys())}")
    for name, pin in projects.items():
        checkout = root / name
        if checkout.is_symlink() or not (checkout / ".git").is_dir():
            raise ValueError(f"expected a prepared Git checkout: {checkout}")
        if git(checkout, "rev-parse", "--verify", "HEAD") != pin["commit"]:
            raise ValueError(f"{name} does not match locked commit {pin['commit']}")
        if any(git(checkout, "config", "--local", "--get", key) != value
               for key, value in CHECKOUT_SETTINGS.items()):
            raise ValueError(f"source checkout settings differ from preparation: {checkout}")
        if git(checkout, "status", "--porcelain=v1", "--untracked-files=all", "--ignored"):
            raise ValueError(f"source checkout is dirty: {checkout}")


def prepare(root: Path, cache: Path, projects: dict, offline: bool) -> None:
    if root.exists() or root.is_symlink():
        raise ValueError(f"destination already exists: {root}")
    root.parent.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".prepare-", dir=root.parent) as temp:
        tree = Path(temp)
        for name, pin in projects.items():
            commit = pin["commit"]
            key = hashlib.sha256(pin["url"].encode()).hexdigest()
            repository = cache / f"{key}.git"
            with (cache / f"{key}.lock").open("a") as mutex:
                fcntl.flock(mutex, fcntl.LOCK_EX)
                if not repository.exists():
                    if offline:
                        raise ValueError(f"no cached repository for {name}")
                    git(cache, "init", "--bare", "--quiet", str(repository))
                ref = f"refs/source-locks/{commit}"
                cached_commit = subprocess.run(
                    ["git", "-C", str(repository), "show-ref", "--verify", "--quiet", ref]
                ).returncode == 0
                if not cached_commit:
                    if offline:
                        raise ValueError(f"no cached commit for {name}: {commit}")
                    print(f"Fetching {name} at {commit}", flush=True)
                    git(repository, "fetch", "--quiet", "--depth=1", "--no-tags",
                        pin["url"], f"{commit}:{ref}")
                checkout = tree / name
                git(tree, "init", "--quiet", "--template=", str(checkout))
                git(checkout, "fetch", "--quiet", "--depth=1", "--no-tags", str(repository), ref)
            for key, value in CHECKOUT_SETTINGS.items():
                git(checkout, "config", "--local", key, value)
            git(checkout, "checkout", "--quiet", "--detach", commit)
        verify(tree, projects)
        tree.rename(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "verify"):
        command = commands.add_parser(name)
        command.add_argument("--sdk", required=True)
        command.add_argument("--profile", choices=["objc4"])
        command.add_argument("--source-root", type=Path)
    commands.choices["prepare"].add_argument("--cache", type=Path, default=ROOT / "build/source-cache")
    commands.choices["prepare"].add_argument("--offline", action="store_true")
    commands.choices["verify"].add_argument("--record", type=Path,
                                           help="write the verified source lock to a new file")
    args = parser.parse_args()
    try:
        lock_bytes, projects = read_lock(args.sdk, args.profile)
        directory = f"{args.sdk}-{args.profile}" if args.profile else args.sdk
        root = (args.source_root or ROOT / "build/sources" / directory).absolute()
        if args.command == "prepare":
            prepare(root, args.cache.resolve(), projects, args.offline)
            print(f"{args.sdk}: prepared {len(projects)} projects at {root}")
        else:
            verify(root, projects)
            if args.record:
                with args.record.open("xb") as record:
                    record.write(lock_bytes)
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
