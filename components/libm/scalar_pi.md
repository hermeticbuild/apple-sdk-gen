# macOS scalar cosine-pi and tangent-pi

The Libm-2026 dispatcher and its arm64 and x86_64 headers omit the scalar
cosine-pi and tangent-pi declarations. Apple's open-source Clang registers
each with `math.h`. The unsuffixed functions take and return `double`. The
`f` functions take and return `float`. Apple's WWDC 2013 session 713
identifies all four functions as new in macOS 10.9 and iOS 7. The macOS
dispatcher adds them under its existing architecture, availability and
C linkage rules.
[Pinned Libm source](https://github.com/apple-oss-distributions/Libm/tree/17a5f9daa3f5679f7536b26f133b40cc078753c3/Source) ·
[Apple Clang builtin records](https://github.com/apple-oss-distributions/clang/blob/8204159ac8569f29fddc48862412243c2b79ce8c/src/tools/clang/include/clang/Basic/Builtins.def#L1181-L1190) ·
[Apple WWDC 2013 Session 713 slides](https://docs.huihoo.com/apple/wwdc/2013/session_713__accelerate_framework.pdf)

LLVM 23.1.2 independently applies the macOS 10.9 libcall boundary to the
cosine-pi pair. The [installed-header fixture](../../tests/installed_headers/libm_scalar_pi.c)
checks the four signatures, exact cosine at a half turn, exact tangent at a
negative quarter turn and signed zero.
[LLVM deployment predicate](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/lib/Analysis/TargetLibraryInfo.cpp#L38-L54) ·
[LLVM cosine-pi gating](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/lib/Analysis/TargetLibraryInfo.cpp#L186-L193)

## Qualification

Clang 23.1.2 failed to find all four declarations in the original
installed headers. The repaired headers and the macOS 26.5 SDK (25F70)
both compiled the fixture in default, ANSI, POSIX and Darwin C11 modes
on arm64 and x86_64. With `-Werror -Wunguarded-availability`, both
headers rejected all four calls at x86_64 macOS 10.8 and accepted
them at 10.9.

C11 and C++17 objects at O0 and O2 imported all four Darwin symbols.
The fixture linked through libSystem and ran on macOS 26.5.2 (25F84)
on native arm64 and Rosetta x86_64. Local `dyld_info` captured the
four exports in `/usr/lib/system/libsystem_m.dylib` in the arm64e image
`A7E0863C-101A-31A0-922B-ED9B02626151` and x86_64 image
`A0E06486-747D-3935-8EF2-D89AA45FFE13`. The x86_64 `___cospif` export
uses a runtime resolver.

The generated link interface stores strong function exports in
`libsystem_m` for both targets. Pinned LLD 23.1.2 at the macOS 11.0
deployment floor reported all four symbols undefined before adding
the reviewed exports. Afterward the generated and reference links
had identical strong imports, dependency and deployment metadata.
The executables linked against the generated interface ran on both
architectures.
