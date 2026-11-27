"""Regression checks for the expected-undefined evidence boundary."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from .verify_unistd_expected_undefined import check_lookup


class ExpectedUndefinedLookupTest(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.sdk = Path(tmp.name).resolve()
        self.symbols = ["_add_profil", "_profil", "_unwhiteout"]
        self.summary = {"issues": 0, "parsed_paths": 3, "physical_paths": 3, "documents": 4}

    def lookup(self):
        return {
            "schema": 1, "sdk": str(self.sdk), "reader_sha256": "fixture",
            "summary": self.summary, "complete": True, "issues": [], "queries": self.symbols,
            "raw_candidates": {symbol: [] for symbol in self.symbols},
            "raw_directive_candidates": {symbol: [] for symbol in self.symbols},
            "matches": [], "linker_directives": [],
        }

    def test_requires_complete_raw_lookup(self):
        lookup = self.lookup()
        self.assertEqual(check_lookup(self.sdk, lookup, self.symbols, "fixture"), self.summary)
        del lookup["raw_directive_candidates"]["_profil"]
        with self.assertRaisesRegex(ValueError, "--raw-symbol"):
            check_lookup(self.sdk, lookup, self.symbols, "fixture")
        lookup = self.lookup()
        lookup["summary"] = {**self.summary, "parsed_paths": 2}
        with self.assertRaisesRegex(ValueError, "lookup is incomplete"):
            check_lookup(self.sdk, lookup, self.symbols, "fixture")

    def test_reopens_for_each_kind_of_reported_match(self):
        cases = {
            "matches": [{"symbol": "_profil", "role": "reexport"}],
            "linker_directives": [{"symbol": "_profil", "directive": "$ld$hide$os11.0$_profil"}],
            "raw_candidates": {**dict.fromkeys(self.symbols, []), "_profil": ["usr/lib/provider.tbd"]},
            "raw_directive_candidates": {**dict.fromkeys(self.symbols, []), "_profil": ["usr/lib/provider.tbd"]},
        }
        for key, value in cases.items():
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "reopen.*_profil"):
                check_lookup(self.sdk, {**self.lookup(), key: value}, self.symbols, "fixture")


if __name__ == "__main__":
    unittest.main()
