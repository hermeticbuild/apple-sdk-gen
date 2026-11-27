"""Install LLVM release headers configured for the macOS system libc++."""

import shutil
import subprocess
from pathlib import Path

DATA = Path(__file__).with_name("data")


def install_libcxx_headers(sdk_root: Path, llvm_dir: Path) -> None:
    source = llvm_dir / "include/c++/v1"
    destination = sdk_root / "usr/include/c++/v1"
    shutil.copytree(source, destination, dirs_exist_ok=True)
    for patch in ("libcxx-apple-config.patch", "libcxx-apple-availability.patch"):
        subprocess.run(["patch", "-s", "-f", "-F", "0", "-p0", "-d", destination,
                        "-i", DATA / patch], check=True)
    for component in ("libcxx", "libcxxabi"):
        license_dir = sdk_root / "usr/share/licenses" / component
        license_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DATA / f"{component}-LICENSE.txt", license_dir / "LICENSE.TXT")
