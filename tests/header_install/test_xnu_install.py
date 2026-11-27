"""Exercise the public XNU headers and source receipts in a real installation."""

import os
from pathlib import Path
import unittest

from tools.header_manifest import read_header_manifest


@unittest.skipUnless(os.getenv("C_INSTALL"), "requires the output of make install")
class XnuInstallTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers, _ = read_header_manifest(Path(os.environ["C_INSTALL"]))

    def test_public_install_keeps_private_and_empty_headers_out(self):
        self.assertEqual(self.headers["usr/include/sys/socket.h"]["owner"], "xnu")
        self.assertNotIn("usr/include/sys/proc_private.h", self.headers)
        self.assertNotIn("usr/include/mach/syscall_sw.h", self.headers)

    def test_asm_header_records_actual_input_from_xnu_vpath(self):
        arm = self.headers["usr/include/mach/arm64/asm.h"]
        self.assertIn("sources/xnu/osfmk/arm64/asm.h", arm["inputs"])
        self.assertEqual(arm["selection"], "osfmk/mach/arm64/Makefile:INSTALL_MD_GEN_LIST")

    def test_generated_headers_record_syscall_and_availability_inputs(self):
        syscall = self.headers["usr/include/sys/syscall.h"]
        alias = self.headers["usr/include/sys/_symbol_aliasing.h"]
        self.assertIn("sources/xnu/bsd/kern/syscalls.master", syscall["inputs"])
        self.assertIn("sources/AvailabilityVersions/availability.dsl", alias["inputs"])
