#!/usr/bin/env python3
"""Resolve the SHA256-pinned @llvm minimal prebuilt from hermetic-llvm Bazel."""

import argparse
import json
import platform
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
PIN = HERE / "data/llvm-minimal-prebuilt.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llvm-repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.llvm_repo.resolve()
    pin = json.loads(PIN.read_text())
    index = json.loads((repo / "extensions/llvm_toolchain_minimal_index.json").read_text())
    release = index["latest_by_llvm_version"].get(pin["llvm_version"])
    if release != pin["release"]:
        parser.error("hermetic-llvm selected a different minimal-prebuilt release")
    machine = {"x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(
        platform.machine().lower())
    system = platform.system().lower()
    if system not in ("darwin", "linux") or machine is None or (system == "darwin" and machine != "arm64"):
        parser.error("no pinned minimal-prebuilt archive for this host")
    archive_target = f"{system}-{machine}" + ("-musl" if system == "linux" else "")
    if index["releases"][release][archive_target] != pin["archives"][archive_target]:
        parser.error("hermetic-llvm minimal-prebuilt index differs from pinned archive")
    repo_target = archive_target.removesuffix("-musl")
    target = f"@llvm-toolchain-minimal-{repo_target}//:clang"
    subprocess.run(["bazel", "fetch", "--config=remote", target],
                   cwd=repo, check=True, stdout=subprocess.DEVNULL)
    output_base = subprocess.check_output(
        ["bazel", "info", "output_base", "--config=remote"],
        cwd=repo, text=True).strip()
    clang = Path(output_base) / (
        f"external/+llvm_toolchain_minimal+llvm-toolchain-minimal-{repo_target}/bin/clang")
    if not clang.is_file():
        parser.error(f"fetched prebuilt clang not found: {clang}")
    resource = subprocess.check_output(
        [str(clang), "-print-resource-dir"], text=True).strip()
    if not (Path(resource) / "include").is_dir():
        parser.error("fetched prebuilt has no Clang resource headers")
    print(clang)


if __name__ == "__main__":
    main()
