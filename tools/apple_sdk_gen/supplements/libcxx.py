"""Install C++ standard library headers from official LLVM releases."""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

logger = logging.getLogger(__name__)

_MACOS_26_5_LLVM_VERSION = "21.1.6"
_MACOS_26_5_LLVM_SHA256 = {
    "cmake": "e364f135fa14c343d70cac96f577f44e8e20bf026682f647f8c3c5687a0bebd1",
    "libcxx": "500b13d4ddc24733549b55a2584143274c7004966dcd6f5f98e5a22f7bfe9fd5",
    "libcxxabi": "984dfc757fed1e4e9f668240bc0d4a6c60ca9406269d045462c0afe9ce0e85d9",
    "llvm": "908bce97be0275943414b45af2e2b20e8f6d5d9266fdc120bd59f096ebc547ad",
    "runtimes": "3b2dcaec1163caf067988228c1d21a75334c47d22610956dd9699ea0631bce45",
}

_RELEASE_URL = (
    "https://github.com/llvm/llvm-project/releases/download/"
    "llvmorg-{version}/{component}-{version}.src.tar.xz"
)


def install_libcxx_headers(
    sdk_root: Path,
    sdk_version: str,
    cache_dir: Path,
) -> None:
    """Run LLVM's header install targets with the release's Apple preset."""
    if sdk_version != "26.5":
        raise ValueError(f"No pinned libc++ sources for macOS SDK {sdk_version}")
    version = _MACOS_26_5_LLVM_VERSION
    cache_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="libcxx-", dir=cache_dir) as temporary:
        work = Path(temporary).resolve()
        for component, sha256 in _MACOS_26_5_LLVM_SHA256.items():
            prefix = f"{component}-{version}.src"
            archive = cache_dir / f"{prefix}.tar.xz"
            if not archive.is_file():
                url = _RELEASE_URL.format(version=version, component=component)
                logger.info("Downloading %s", url)
                download = work / archive.name
                with urlopen(url, timeout=120) as response, download.open("wb") as output:
                    shutil.copyfileobj(response, output)
                _check_release_hash(download, sha256)
                download.replace(archive)
            else:
                _check_release_hash(archive, sha256)

            with tarfile.open(archive) as source:
                members = None
                if component == "llvm":
                    required = (f"{prefix}/cmake/", f"{prefix}/utils/")
                    members = (member for member in source
                               if member.name.startswith(required))
                source.extractall(work, members=members, filter="data")
            (work / prefix).rename(work / component)

        build = work / "build"
        install = work / "install"
        target = "arm64-apple-macos11.0"
        _cmake([
            "-G", "Ninja", "-S", str(work / "runtimes"), "-B", str(build),
            "-C", str(work / "libcxx/cmake/caches/Apple.cmake"),
            "-DLLVM_ENABLE_RUNTIMES=libcxx;libcxxabi",
            "-DCMAKE_SYSTEM_NAME=Darwin", "-DCMAKE_OSX_ARCHITECTURES=arm64",
            f"-DCMAKE_OSX_SYSROOT={sdk_root.resolve()}", "-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0",
            "-DCMAKE_C_COMPILER=clang", f"-DCMAKE_C_COMPILER_TARGET={target}",
            "-DCMAKE_CXX_COMPILER=clang++", f"-DCMAKE_CXX_COMPILER_TARGET={target}",
            "-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY",
            f"-DCMAKE_INSTALL_PREFIX={install}",
            "-DLLVM_INCLUDE_TESTS=OFF", "-DLIBCXX_INCLUDE_TESTS=OFF",
            "-DLIBCXXABI_INCLUDE_TESTS=OFF",
        ])
        _cmake([
            "--build", str(build),
            "--target", "install-cxx-headers", "install-cxxabi-headers",
        ])
        destination = sdk_root / "usr/include/c++/v1"
        shutil.copytree(install / "include/c++/v1", destination, dirs_exist_ok=True)
        for component in ("libcxx", "libcxxabi"):
            license_dir = sdk_root / "usr/share/licenses" / component
            license_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(work / component / "LICENSE.TXT", license_dir / "LICENSE.TXT")
    logger.info("Installed LLVM %s libc++ and libc++abi headers into %s", version, destination)


def _cmake(args: list[str]) -> None:
    result = subprocess.run(
        ["cmake", *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    if result.returncode:
        raise RuntimeError(f"CMake failed:\n{result.stdout[-8192:]}")


def _check_release_hash(path: Path, expected: str) -> None:
    with path.open("rb") as archive:
        digest = hashlib.file_digest(archive, "sha256").hexdigest()
    if digest != expected:
        raise ValueError(f"{path}: SHA-256 is {digest}, expected {expected}")
