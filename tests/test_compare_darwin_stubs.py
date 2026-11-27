import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.apple_sdk_gen.generators.render_tbd import tbd_document
from tools.apple_sdk_gen.supplements.install_darwin_stubs import LIBRARIES, TARGET


CHILD = "/usr/lib/system/libsystem_test.dylib"


class CompareDarwinStubsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write_sdk(self, name, exports, *, target=TARGET, reexport=True):
        sdk = self.root / name
        lib = sdk / "usr/lib"
        lib.mkdir(parents=True)
        for stub, provider in LIBRARIES.items():
            document = tbd_document(
                [target], provider,
                reexports=[CHILD] if stub == "libSystem.B" and reexport else [],
            )
            if stub == "libSystem.B":
                document += tbd_document([target], CHILD, exports=[([target], exports)])
            (lib / f"{stub}.tbd").write_text(document)
        return sdk

    def compare(self, baseline, candidate, *flags):
        result = subprocess.run(
            [sys.executable, "-m", "tools.apple_sdk_gen.compare_darwin_stubs",
             baseline, candidate, *flags],
            check=False, capture_output=True, text=True,
        )
        self.assertIn(result.returncode, {0, 1}, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def test_addition_passes_but_changed_kind_and_lost_reexport_fail(self):
        baseline = self.write_sdk("before", {"symbols": ["_first"]})
        added = self.write_sdk("added", {"symbols": ["_first", "_second"]})
        self.assertEqual(self.compare(baseline, added)[0], 0)

        changed = self.write_sdk("changed", {"weak-symbols": ["_first"]}, reexport=False)
        status, report = self.compare(baseline, changed)
        self.assertEqual(status, 1)
        self.assertEqual(
            {entry["kind"] for entry in report["unapproved_removals"]},
            {"exports.symbols", "reexported-libraries.libraries"},
        )

    def test_empty_child_requires_an_exact_approval(self):
        baseline = self.write_sdk("before", {"symbols": ["_first"]})
        candidate = self.write_sdk("after", {})
        status, report = self.compare(baseline, candidate)
        self.assertEqual(status, 1)
        self.assertEqual(report["emptied_providers"], [["libSystem.B.tbd", CHILD]])

        approvals = self.root / "approved.tsv"
        approvals.write_text(
            "stub\tprovider\tkind\tname\treason\n"
            f"libSystem.B.tbd\t{CHILD}\texports.symbols\t_first\tRemoved unsupported test API\n"
        )
        self.assertEqual(self.compare(baseline, candidate, "--approved-removals", approvals)[0], 0)
        status, report = self.compare(candidate, candidate, "--approved-removals", approvals)
        self.assertEqual(status, 1)
        self.assertEqual(len(report["stale_approvals"]), 1)

    def test_report_only_compares_apple_arm64e_provider(self):
        baseline = self.write_sdk("reference", {"symbols": ["_first"]}, target="arm64e-macos")
        candidate = self.write_sdk("after", {})
        status, report = self.compare(baseline, candidate, "--report-only")
        self.assertEqual(status, 0)
        self.assertEqual([entry["name"] for entry in report["removed"]], ["_first"])
