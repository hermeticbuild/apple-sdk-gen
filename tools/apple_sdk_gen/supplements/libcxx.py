"""Install LLVM release headers configured for the macOS system libc++."""

import shutil
import subprocess
from pathlib import Path

DATA = Path(__file__).with_name("data")


def install_libcxx_headers(sdk_root: Path, sdk_version: str, llvm_dir: Path) -> None:
    if sdk_version != "26.5":
        raise ValueError(f"No libc++ header configuration for macOS SDK {sdk_version}")
    source = llvm_dir / "include/c++/v1"
    destination = sdk_root / "usr/include/c++/v1"
    shutil.copytree(source, destination, dirs_exist_ok=True)
    subprocess.run(["patch", "-s", "-f", "-F", "0", "-p0", "-d", destination,
                    "-i", DATA / "libcxx-apple-config.patch"], check=True)
    for component in ("libcxx", "libcxxabi"):
        license_dir = sdk_root / "usr/share/licenses" / component
        license_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DATA / f"{component}-LICENSE.txt", license_dir / "LICENSE.TXT")
