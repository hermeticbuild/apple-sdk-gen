"""Exercise the shell merge against real staged files and provenance records."""

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.header_manifest import read_header_manifest

ROOT = Path(__file__).resolve().parents[2]
HEADER = "usr/include/example.h"
RULE = "recipes/libm/Makefile"
SOURCE = "sources/Libm/Source/math.h"


class MergeTest(unittest.TestCase):
    def stage(self, root: Path, owner: str, path: str = HEADER) -> Path:
        target = root / owner / "dst" / HEADER
        target.parent.mkdir(parents=True)
        target.write_bytes(b"example\n")
        target.chmod(0o444)
        receipt = root / owner / "records"
        receipt.write_text("\t".join((path, owner, SOURCE, RULE, "copy", RULE, SOURCE)) + "\n")
        return receipt

    def merge(self, output: Path, *receipts: Path, bootstrap: bool = False):
        options = ["--bootstrap"] if bootstrap else []
        sources = output.parent / "sources"
        source = sources / SOURCE.removeprefix("sources/")
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"upstream example\n")
        environment = dict(os.environ, SOURCE_ROOT=str(sources))
        environment.pop("SOURCE_LOCK", None)
        return subprocess.run(
            ["/bin/sh", "recipes/merge.sh", *options, str(output), *map(str, receipts)],
            cwd=ROOT, capture_output=True, text=True, env=environment,
        )

    def test_install_records_the_header_and_its_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "out"
            result = self.merge(output, self.stage(root, "Libm"))
            self.assertEqual(result.returncode, 0, result.stderr)
            data = (output / HEADER).read_bytes()
            self.assertEqual(data, b"example\n")
            self.assertEqual((output / HEADER).stat().st_mode & 0o777, 0o644)
            files, _ = read_header_manifest(output)
            self.assertEqual(files[HEADER]["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(files[HEADER]["inputs"], [RULE, SOURCE])

    def test_bootstrap_installs_headers_without_a_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "out"
            result = self.merge(output, self.stage(root, "Libm"), bootstrap=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output / HEADER).is_file())
            self.assertEqual(list(output.iterdir()), [output / "usr"])

    def test_unrecorded_header_fails_before_publishing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "out"
            receipt = self.stage(root, "Libm")
            (receipt.parent / "dst/usr/include/extra.h").touch()
            result = self.merge(output, receipt)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("stage paths differ", result.stderr)
            self.assertFalse(output.exists())

    def test_duplicate_paths_fail_before_any_output_is_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "out"
            result = self.merge(output, self.stage(root, "Libm"), self.stage(root, "other"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("multiple owners", result.stderr)
            self.assertFalse(output.exists())

    def test_paths_cannot_escape_the_public_include_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "out"
            result = self.merge(output, self.stage(root, "Libm", "usr/include/../x.h"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("stage paths differ", result.stderr)
            self.assertFalse(output.exists())
