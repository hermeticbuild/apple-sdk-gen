#!/usr/bin/env python3
"""Check the public-source arm64 fenv derivation against macOS libSystem."""

import ctypes
import platform

if platform.system() != "Darwin" or platform.machine() != "arm64":
    print("SKIP fenv runtime check: requires arm64 macOS")
    raise SystemExit(0)

lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
lib.fegetenv.argtypes = [ctypes.c_void_p]
lib.fesetround.argtypes = [ctypes.c_int]
lib.fegetround.restype = ctypes.c_int

original_rounding = lib.fegetround()
try:
    for mode in (0, 1 << 22, 2 << 22, 3 << 22):
        assert lib.fesetround(mode) == 0
        assert lib.fegetround() == mode
        buffer = ctypes.create_string_buffer(32)
        ctypes.memset(buffer, 0xa5, 32)
        assert lib.fegetenv(buffer) == 0
        fpsr = int.from_bytes(buffer.raw[:8], "little")
        fpcr = int.from_bytes(buffer.raw[8:16], "little")
        assert fpcr & (3 << 22) == mode
        assert buffer.raw[16:] == b"\xa5" * 16
        print(f"mode={mode:#x} fpsr={fpsr:#x} fpcr={fpcr:#x}")
finally:
    lib.fesetround(original_rounding)
