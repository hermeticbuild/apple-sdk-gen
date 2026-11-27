"""Install LLVM release headers configured for the macOS system libc++."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

DATA = Path(__file__).with_name("data")
LLVM_PIN = DATA / "llvm-macos-arm64.json"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_digest(path: Path, expected: str | None) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"missing regular file: {path}")
    if expected is not None and sha256(path) != expected:
        raise ValueError(f"SHA-256 mismatch: {path}")


def cache_file(path: Path, fetch, offline: bool, expected: str | None = None) -> Path:
    if path.exists() or path.is_symlink():
        check_digest(path, expected)
        return path
    if offline:
        raise ValueError(f"offline mode requires cached input: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=path.parent) as temporary:
        incoming = Path(temporary) / path.name
        fetch(incoming)
        check_digest(incoming, expected)
        incoming.replace(path)
    return path


def fetch_asset(cache: Path, asset: dict, offline: bool = False) -> Path:
    url = asset["url"]

    def download(path: Path) -> None:
        with urlopen(url, timeout=120) as response, path.open("wb") as output:
            shutil.copyfileobj(response, output)

    return cache_file(cache / url.rsplit("/", 1)[-1], download, offline, asset["sha256"])


def copy_headers(source: Path, sdk_root: Path) -> None:
    destination = sdk_root / "usr/include/c++/v1"
    shutil.copytree(source, destination, dirs_exist_ok=True)
    subprocess.run(["patch", "-s", "-f", "-F", "0", "-p0", "-d", destination,
                    "-i", DATA / "libcxx-apple-config.patch"], check=True)
    for component in ("libcxx", "libcxxabi"):
        license_dir = sdk_root / "usr/share/licenses" / component
        license_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DATA / f"{component}-LICENSE.txt", license_dir / "LICENSE.TXT")


def install_libcxx_headers(sdk_root: Path, sdk_version: str, cache_dir: Path,
                           llvm_dir: Path | None = None) -> None:
    if sdk_version != "26.5":
        raise ValueError(f"No pinned libc++ headers for macOS SDK {sdk_version}")
    lock = json.loads(LLVM_PIN.read_text())
    headers = Path(lock["cxx_headers"]["path"])
    if llvm_dir is not None:
        copy_headers(llvm_dir / headers, sdk_root)
        return

    # The standalone generator can install the headers on any host.
    archive = fetch_asset(cache_dir, lock["archive"])
    prefix = Path(lock["archive"]["directory"]) / headers
    with TemporaryDirectory(prefix="libcxx-", dir=cache_dir) as temporary:
        with tarfile.open(archive) as source:
            members = (member for member in source
                       if Path(member.name).is_relative_to(prefix))
            source.extractall(temporary, members=members, filter="data")
        copy_headers(Path(temporary) / prefix, sdk_root)
