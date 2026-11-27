"""Exercise the reference lookup with versioned and embedded fixture stubs."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from .lookup_tbd_symbols import directive_symbol, raw_candidates


LLVM = os.getenv("LIBSYSTEM_TEST_LLVM")
FIXTURE = """--- !tapi-tbd
tbd-version: 4
targets: [ arm64-macos, x86_64-macos ]
install-name: '/Framework/Fixture'
reexported-libraries:
  - targets: [ arm64-macos, x86_64-macos ]
    libraries: [ '/usr/lib/libChild.dylib' ]
reexports:
  - targets: [ x86_64-macos ]
    symbols: [ _forwarded ]
--- !tapi-tbd
tbd-version: 4
targets: [ arm64-macos, x86_64-macos ]
install-name: '/usr/lib/libChild.dylib'
exports:
  - targets: [ arm64-macos ]
    symbols: [ _needle, _same_prefix, _mixed, '$ld$hide$os11.0$_blocked' ]
    objc-classes: [ Object ]
reexports:
  - targets: [ x86_64-macos ]
    symbols: [ _mixed ]
...
"""


class TokenTests(unittest.TestCase):
    def test_raw_spelling_and_directives_are_separate(self):
        source = b"[ '_ordinary', _prefix_other, '$ld$hide$os11.0$_old', '$ld$previous$/Lib$$1$11$14$_prior$' ]"
        self.assertEqual(raw_candidates(source, ["_ordinary", "_prefix", "_old", "_prior"]),
                         (["_ordinary"], ["_old", "_prior"]))
        self.assertEqual(directive_symbol("$ld$previous$/Lib$$1$11$14$_has$dollar$"), "_has$dollar")


@unittest.skipUnless(LLVM, "set LIBSYSTEM_TEST_LLVM to the verified LLVM bundle")
class LookupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.sdk = self.work / "Fixture SDK"
        versioned = self.sdk / "PrivateFrameworks/Fixture.framework/Versions"
        (versioned / "A").mkdir(parents=True)
        (versioned / "A/Fixture.tbd").write_text(FIXTURE)
        (versioned / "Current").symlink_to("A")
        (versioned.parent / "Fixture.tbd").symlink_to("Versions/Current/Fixture.tbd")
        self.physical = "PrivateFrameworks/Fixture.framework/Versions/A/Fixture.tbd"
        self.out = self.work / "audit.json"

    def lookup(self):
        return subprocess.run([
            sys.executable, "-m", "sdk_review.linkage.lookup_tbd_symbols",
            "--sdk", self.sdk, "--llvm", LLVM, "--out", self.out,
            "--raw-symbol", "_needle", "--raw-symbol", "_same",
            "--raw-symbol", "_blocked", "--symbol", "_forwarded",
            "--symbol", "_OBJC_METACLASS_$_Object", "--symbol", "_mixed",
        ], capture_output=True, text=True)

    def test_finds_embedded_provider_and_explicit_reexports(self):
        result = self.lookup()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(self.out.read_text())
        self.assertTrue(report["complete"])
        self.assertEqual(report["summary"], {"physical_paths": 1, "parsed_paths": 1, "documents": 2,
                                             "tbd_aliases": 1, "directory_aliases": 1, "issues": 0})
        self.assertEqual(report["tbd_aliases"]["PrivateFrameworks/Fixture.framework/Fixture.tbd"], self.physical)
        self.assertEqual({row["symbol"]: (row["document"], row["role"], row["targets"])
                          for row in report["matches"] if row["symbol"] != "_mixed"}, {
            "_needle": (2, "export", ["arm64-macos"]),
            "_forwarded": (1, "reexport", ["x86_64-macos"]),
            "_OBJC_METACLASS_$_Object": (2, "export", ["arm64-macos"]),
        })
        self.assertEqual({row["role"]: row["targets"] for row in report["matches"]
                          if row["symbol"] == "_mixed"},
                         {"export": ["arm64-macos"], "reexport": ["x86_64-macos"]})
        self.assertEqual(report["reexport_edges"][0]["matched_targets"], ["arm64-macos", "x86_64-macos"])
        self.assertEqual([row["symbol"] for row in report["linker_directives"]], ["_blocked"])
        self.assertEqual(report["raw_candidates"], {"_blocked": [], "_needle": [self.physical], "_same": []})
        self.assertEqual(report["raw_directive_candidates"]["_blocked"], [self.physical])

    def test_reports_escaping_broken_and_unreadable_paths(self):
        external = self.work / "external.tbd"
        external.write_text(FIXTURE.replace("_needle", "_external"))
        (self.sdk / "escaping.tbd").symlink_to(external)
        (self.sdk / "dangling.tbd").symlink_to("missing.tbd")
        (self.sdk / "malformed.tbd").write_text("malformed")
        result = self.lookup()
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(self.out.read_text())
        self.assertFalse(report["complete"])
        self.assertEqual({row["path"] for row in report["issues"]},
                         {"escaping.tbd", "dangling.tbd", "malformed.tbd"})
        self.assertEqual({row["path"] for row in report["matches"]}, {self.physical})
