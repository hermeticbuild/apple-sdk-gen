# Verify binary16 math linkage and runtime

The [binary16 declarations](../../../../../../recipes/libm/half_math.md) have a syntax-only check in `make test` for 26.5.

The [runtime fixture](../../../../../../tests/installed_headers/libm_half.c)
checks each C function type, calls all thirteen functions, verifies the
provider address with `dladdr`, and prints the binary16 result bits for
comparison with the same client built using the reference SDK. Use the
following commands with `T` set to a target such as `arm64-apple-macos15.0`.
Set `C_INSTALL` to the standalone header tree and `STUBS` to the composed or reference SDK used for linking.

```sh
clang="$LLVM/bin/clang"
resource=$("$clang" -print-resource-dir)
"$clang" --no-default-config -target "$T" -nostdinc -isystem "$resource/include" \
    -isystem "$C_INSTALL/usr/include" -std=c11 -D_DARWIN_C_SOURCE -fno-builtin \
    -O2 -Werror=unguarded-availability-new -c -DTEST_HALF_RUNTIME tests/installed_headers/libm_half.c -o half.o
"$LLVM/bin/llvm-nm" -mu half.o
"$clang" --no-default-config -target "$T" -nostdlib -fuse-ld=lld \
    -isysroot "$STUBS" half.o -lSystem -o half
./half
```

At minima 11.0 and 14.7 the strict compile must diagnose unguarded uses.
Repeat with `-Wno-unguarded-availability-new` to inspect all thirteen weak
imports. The imports are strong at minima 15.0 and 26.5. Both targets produced
SDK-identical objects and runtime outputs at all four minima on macOS 26.5.2.
Rosetta's deployed `__rintf16(1.25)` returned 1.25 in the control and
candidate. Historical cache inspection establishes export presence only.

With `-DTEST_HALF_WIDEN` the Intel client also imports the compiler helper
`__extendhfsf2` to print a floating-point result. The reference SDK resolves
this helper. The historical standalone stub experiment left it to the compiler runtime.
The installed hermetic-llvm Intel builtins archive satisfied it at 15.0
and 26.5. The archive's minimum is 14.0. For 11.0 the pinned LLVM
`extendhfsf2.c` compiled at 11.0 satisfied the same link with fatal linker
warnings enabled. Both variants ran under Rosetta. This separate compiler
binding remains a difference for clients linking with `-nostdlib`.
[LLVM implementation](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/compiler-rt/lib/builtins/extendhfsf2.c)
