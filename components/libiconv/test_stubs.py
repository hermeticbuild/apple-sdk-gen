"""Exercise source-only production and two-level namespace binding on arm64 macOS."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from components.libiconv.generate_stubs import generate, REVISION
from tools.tbd import read_stub
from tools import fetch_llvm_tools


INPUTS = ("ICONV_SOURCE", "C_INSTALL", "LLVM")
STUBS = ("libiconv.2", "libcharset.1")


@unittest.skipUnless(all(os.getenv(k) for k in INPUTS), "set ICONV_SOURCE, C_INSTALL and LLVM")
class IconvStubsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.work = Path(tmp.name)
        cls.source, cls.headers, cls.llvm = (Path(os.environ[k]).resolve() for k in INPUTS)
        cls.sdk = cls.work / "output"
        generate(cls.source, cls.headers, cls.llvm, cls.sdk)

    def test_repeat_generation(self):
        repeat = self.work / "repeat"
        generate(self.source, self.headers, self.llvm, repeat)
        self.assertEqual((self.sdk / "manifest.json").read_bytes(), (repeat / "manifest.json").read_bytes())
        for lib in STUBS:
            path = Path("usr/lib") / (lib + ".tbd")
            alias = path.with_name(lib.split(".")[0] + ".tbd")
            self.assertEqual((self.sdk / path).read_bytes(), (repeat / path).read_bytes())
            for root in self.sdk, repeat:
                self.assertEqual((root / alias).readlink(), Path(path.name))

    def test_link_through_iconv(self):
        # The standalone C inventory carries iconv.h. Get the separate public charset
        # header from the pinned source so its declaration is checked by the consumer.
        (self.work / "localcharset.h").write_bytes(subprocess.check_output([
            "git", "-C", self.source, "show", REVISION + ":libcharset/localcharset.h",
        ]))
        source = self.work / "client.c"
        source.write_text(
            "#include <iconv.h>\n#include <localcharset.h>\n"
            "__typeof__(&iconv_open) opener = &iconv_open;\n"
            "__typeof__(&locale_charset) charset = &locale_charset;\n"
        )
        tools = self.llvm / "bin"
        resource = self.llvm / fetch_llvm_tools.read_llvm_lock()["resource_headers"]
        obj = self.work / "client.o"
        client = self.work / "client.dylib"
        subprocess.run([
            tools / "clang", "--no-default-config", "-target", "arm64-apple-macos11",
            "-nostdinc", "-isysroot", self.headers, "-isystem", resource, "-isystem",
            self.headers / "usr/include", "-I", self.work, "-c", source, "-o", obj,
        ], check=True, env={"LC_ALL": "C"})
        link = [tools / "ld64.lld", "-arch", "arm64", "-platform_version", "macos", "11", "26.5",
                "-dylib", "-syslibroot", self.sdk, "-L", self.sdk / "usr/lib", obj, "-o", client]
        wrong = subprocess.run([*link, "-lcharset"], capture_output=True, text=True)
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn("undefined symbol: _iconv_open", wrong.stderr)
        subprocess.run([*link, "-liconv"], check=True)
        nm = subprocess.check_output([tools / "llvm-nm", "-m", "-u", client], text=True)
        self.assertIn("_iconv_open (from libiconv)", nm)
        self.assertIn("_locale_charset (from libcharset)", nm)
        loads = subprocess.check_output([tools / "llvm-objdump", "--macho",
                                         "--dylibs-used", client], text=True)
        for lib in STUBS:
            self.assertIn("/usr/lib/" + lib + ".dylib ", loads)

    @unittest.skipUnless(os.getenv("ICONV_REFERENCE_SDK"), "optional macOS 26.5 reference comparison")
    def test_reference_export_and_reexport_parity(self):
        reference = Path(os.environ["ICONV_REFERENCE_SDK"])
        for lib in STUBS:
            path = Path("usr/lib") / (lib + ".tbd")
            actual, expected = (read_stub((root / path).read_text(), self.llvm / "bin/llvm-readtapi")
                                for root in (self.sdk, reference))
            self.assertEqual(actual.main, expected.main)
            with self.subTest(lib=lib):
                self.assertEqual(set(actual.libraries[actual.main]), {"arm64-macos"})
                a = actual.libraries[actual.main]["arm64-macos"]
                b = expected.libraries[expected.main]["arm64e-macos"]
                self.assertEqual(a.symbols.keys(), b.symbols.keys())
                for symbol in a.symbols:
                    for key in ("role", "weak", "thread_local"):
                        self.assertEqual(a.symbols[symbol][key], b.symbols[symbol][key])
                self.assertEqual(a.reexports, b.reexports)
                for key in ("current_version", "compatibility_version"):
                    self.assertEqual(a.metadata[key], b.metadata[key])


if __name__ == "__main__":
    unittest.main()
