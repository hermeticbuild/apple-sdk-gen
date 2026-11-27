import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest

from tools.header_manifest import COLUMNS

from sdk_review import REPO_ROOT as ROOT

LLVM = os.environ.get("LIBSYSTEM_TEST_LLVM")


@unittest.skipUnless(LLVM, "set LIBSYSTEM_TEST_LLVM to the verified LLVM bundle")
class CInterfaceComparisonTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.work = Path(directory.name)
        self.sdk = self.work / "sdk"
        self.installation = self.work / "install"
        self.report = self.work / "semantics.json"

        self.write(self.sdk / "SDKSettings.json", json.dumps({
            "CanonicalName": "macosx26.5", "Version": "26.5",
        }))
        version = self.sdk / "System/Library/CoreServices/SystemVersion.plist"
        version.parent.mkdir(parents=True)
        version.write_bytes(plistlib.dumps({"ProductBuildVersion": "FIXTURE"}))
        self.write(self.installation / "source-lock.json", json.dumps({
            "schema": 1, "sdk": {"canonical_name": "macosx26.5", "reference_build": "FIXTURE"},
        }))
        self.write(self.sdk / "usr/include/Availability.h",
                   "#include <AvailabilityInternal.h>\n")
        self.write(self.sdk / "usr/include/bits/availability.h", "#define __MAC_26_5 260500\n")
        (self.sdk / "usr/include/AvailabilityInternal.h").symlink_to("bits/availability.h")
        self.write(self.installation / "usr/include/Availability.h", "#define __MAC_26_5 260500\n")
        self.write(self.installation / "usr/include/AvailabilityInternal.h",
                   "/* Fixture fragment not reached by the installed public route. */\n")
        rows = ["\t".join(COLUMNS)]
        for name in ("Availability.h", "AvailabilityInternal.h"):
            path = "usr/include/" + name
            sha256 = hashlib.sha256((self.installation / path).read_bytes()).hexdigest()
            rows.append("\t".join((path, sha256, "fixture", name, "fixture", "copy", name)))
        self.write(self.installation / "header-manifest.tsv", "\n".join(rows) + "\n")

    @staticmethod
    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def compare(self):
        return subprocess.run([
            sys.executable, "-m", "sdk_review.headers.compare_c_interfaces",
            "--sdk", self.sdk, "--installation", self.installation,
            "--clang", Path(LLVM) / "bin/clang", "--out", self.report,
        ], cwd=ROOT, text=True, capture_output=True)

    def test_successful_umbrella_without_the_header_stays_unreached(self):
        result = self.compare()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(self.report.read_bytes())
        target = "arm64-apple-macos14.0"
        self.assertEqual(report["sdk_build"], "FIXTURE")
        self.assertEqual(report["probes"]["include:Availability.h"][target],
                         {"installation": "pass", "sdk": "pass"})
        self.assertEqual(report["headers"]["usr/include/AvailabilityInternal.h"]["include_reached"][target],
                         {"installation": False, "sdk": True})
        self.assertIn({
            "depth": 2, "path": "usr/include/AvailabilityInternal.h",
            "provider": "sysroot", "resolved_path": "usr/include/bits/availability.h",
        }, report["probe_details"]["include:Availability.h"][target]["sdk"]["includes"])

    def test_changed_manifest_bytes_fail_before_compilation(self):
        (self.installation / "usr/include/Availability.h").write_text("/* changed */\n")
        result = self.compare()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("changed installed header: usr/include/Availability.h", result.stderr)
        self.assertFalse(self.report.exists())


if __name__ == "__main__":
    unittest.main()
