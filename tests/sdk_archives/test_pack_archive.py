"""Check release archive bytes and extraction semantics."""

import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

from tools.pack_archive import pack_archive


class ArchiveTests(unittest.TestCase):
    def test_equivalent_sdk_trees_produce_identical_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            first = work / "original/MacOSX.sdk"
            second = work / "rebuilt/MacOSX.sdk"
            for root in (first, second):
                root.mkdir(parents=True)
                (root / "empty").mkdir()
                (root / "links").mkdir()
                (root / "header.h").write_bytes(b"header\n")
                (root / "._ordinary").write_bytes(b"ordinary file")
            os.link(first / "header.h", first / "copy.h")
            (first / "tool").write_bytes(b"tool\n")
            (second / "tool").write_bytes(b"tool\n")
            (second / "copy.h").write_bytes(b"header\n")
            (first / "tool").chmod(0o700)
            (second / "tool").chmod(0o555)
            for root in (first, second):
                (root / "links/alias").symlink_to("../header.h")
            (second / "._copy.h").write_bytes(b"\x00\x05\x16\x07" + bytes(30))
            os.utime(second / "copy.h", (123, 123))
            if sys.platform == "darwin":
                subprocess.run(["xattr", "-w", "org.example.test", "only-on-second",
                                second / "copy.h"], check=True)

            original = work / "original.tar.zst"
            rebuilt = work / "rebuilt.tar.zst"
            self.assertEqual(pack_archive(first, original, "MacOSX.sdk"),
                             pack_archive(second, rebuilt, "MacOSX.sdk"))
            self.assertEqual(original.read_bytes(), rebuilt.read_bytes())
            raw = subprocess.check_output(["zstd", "-dc", original])
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                self.assertEqual(archive.getnames(), [
                    "MacOSX.sdk", "MacOSX.sdk/._ordinary", "MacOSX.sdk/copy.h", "MacOSX.sdk/empty",
                    "MacOSX.sdk/header.h", "MacOSX.sdk/links", "MacOSX.sdk/links/alias", "MacOSX.sdk/tool",
                ])
                for member in archive:
                    self.assertEqual((member.mtime, member.uid, member.gid), (0, 0, 0))
                    self.assertEqual((member.uname, member.gname, member.pax_headers), ("", "", {}))
                self.assertTrue(archive.getmember("MacOSX.sdk/copy.h").isreg())
                self.assertTrue(archive.getmember("MacOSX.sdk/header.h").isreg())
                self.assertTrue(archive.getmember("MacOSX.sdk/empty").isdir())
                alias = archive.getmember("MacOSX.sdk/links/alias")
                self.assertTrue(alias.issym())
                self.assertEqual(alias.linkname, "../header.h")
                self.assertEqual(archive.getmember("MacOSX.sdk/tool").mode, 0o755)
                self.assertEqual(archive.getmember("MacOSX.sdk/header.h").mode, 0o644)
                self.assertEqual(archive.extractfile("MacOSX.sdk/copy.h").read(), b"header\n")

    def test_output_inside_source_is_rejected_through_symlinked_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            link = Path(temp) / "alias"
            link.symlink_to(source)
            with self.assertRaisesRegex(ValueError, "outside the source directory"):
                pack_archive(source, link / "archive.tar.zst", "libSystem")
            self.assertEqual(list(source.iterdir()), [])

    def test_unsupported_entry_preserves_previous_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            os.mkfifo(source / "pipe")
            output = Path(temp) / "libSystem.tar.zst"
            output.write_bytes(b"previous archive")
            with self.assertRaisesRegex(ValueError, "unsupported SDK entry"):
                pack_archive(source, output, "libSystem")
            self.assertEqual(output.read_bytes(), b"previous archive")


if __name__ == "__main__":
    unittest.main()
