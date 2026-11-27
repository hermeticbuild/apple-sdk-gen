import json
import os
from pathlib import Path
import tempfile
import unittest

from sdk_review.headers.isolate_header_differences import compare_pair


@unittest.skipUnless(os.environ.get("LIBSYSTEM_TEST_LLVM"), "set the pinned LLVM path")
class HeaderSubstitutionTest(unittest.TestCase):
    def test_only_the_selected_header_is_substituted(self):
        clang = Path(os.environ["LIBSYSTEM_TEST_LLVM"]) / "bin/clang"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            header = root / "leaf.h"
            header.write_text("#define CALL(x, y) ((x)+(y))\nint foo(void);\n")
            umbrella = root / "umbrella.h"
            umbrella.write_text('#include "leaf.h"\n')
            other = root / "other.h"
            overlay = root / "overlay.json"
            overlay.write_text(json.dumps({
                "version": 0, "use-external-names": False,
                "roots": [{"type": "file", "name": str(header), "external-contents": str(other)}],
            }))

            def run():
                return compare_pair(clang, ["-nostdinc", "-isystem", root],
                                    "umbrella.h", header, overlay)

            other.write_text("/* comment */\n" + header.read_text())
            self.assertEqual(run()["result"], "same-preprocessing")
            other.write_text(header.read_text().replace("(x)+(y)", "(x)-(y)"))
            self.assertEqual(run()["different_macros"], ["CALL"])
            other.write_text(header.read_text().replace("int foo", "float foo"))
            self.assertEqual(run()["result"], "different-preprocessing")
            other.write_text("#error substitution active\n")
            self.assertIn("substitution active", run()["substituted"]["errors"][0])
            umbrella.write_text("")
            self.assertEqual(run()["result"], "header-not-entered")
