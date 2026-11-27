"""Pack a libSystem package or composed SDK as a reproducible .tar.zst."""

import argparse
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile


def add_tree(archive: tarfile.TarFile, path: Path, name: str) -> None:
    status = path.lstat()
    # Construct headers from the payload. TarInfo defaults to epoch time,
    # numeric owner/group zero and empty user/group names.
    member = tarfile.TarInfo(name)
    if stat.S_ISDIR(status.st_mode):
        member.type = tarfile.DIRTYPE
        member.mode = 0o755
        archive.addfile(member)
        for child in sorted(path.iterdir()):
            add_tree(archive, child, f"{name}/{child.name}")
    elif stat.S_ISLNK(status.st_mode):
        member.type = tarfile.SYMTYPE
        member.mode = 0o777
        member.linkname = os.readlink(path)
        archive.addfile(member)
    elif stat.S_ISREG(status.st_mode):
        member.mode = 0o755 if status.st_mode & 0o111 else 0o644
        member.size = status.st_size
        with path.open("rb") as stream:
            if path.name.startswith("._"):
                if stream.read(4) == b"\x00\x05\x16\x07":  # AppleDouble sidecar
                    return
                stream.seek(0)
            archive.addfile(member, stream)
    else:
        raise ValueError(f"unsupported SDK entry: {path}")


def pack_archive(source: Path, output: Path, root_name: str) -> str:
    if Path(root_name).name != root_name or root_name in ("", ".", ".."):
        raise ValueError("archive root name must be a single directory name")
    source = source.resolve(strict=True)
    if not source.is_dir():
        raise ValueError(f"expected a source directory: {source}")
    output = output.parent.resolve() / output.name
    if output.is_relative_to(source):
        raise ValueError("archive output must be outside the source directory")
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        staged = Path(temp) / "archive.tar.zst"
        with staged.open("wb") as compressed:
            with subprocess.Popen(["zstd", "--single-thread", "-6", "-qc"],
                                  stdin=subprocess.PIPE, stdout=compressed) as process:
                with process.stdin as stream:
                    with tarfile.open(fileobj=stream, mode="w|", format=tarfile.PAX_FORMAT) as archive:
                        add_tree(archive, source, root_name)
                if process.wait():
                    raise subprocess.CalledProcessError(process.returncode, process.args)
        digest = hashlib.sha256()
        with staged.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        staged.replace(output)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root-name", required=True, help="top-level directory in the archive")
    args = parser.parse_args()
    try:
        print(pack_archive(args.source, args.output, args.root_name))
    except (OSError, ValueError, subprocess.CalledProcessError) as err:
        parser.exit(1, f"pack-archive: {err}\n")


if __name__ == "__main__":
    main()
