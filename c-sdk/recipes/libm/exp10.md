# macOS base-10 exponential declarations

The Libm-2026 dispatcher and its arm64 and x86_64 headers omit `__exp10` and
`__exp10f`. Apple's open-source Clang registers both with `math.h` and records
their double-to-double (`dd`) and float-to-float (`ff`) signatures. Apple's
macOS 26.5 SDK (25F70) marks both functions available from macOS 10.9. LLVM
23.1.2 independently uses these libcall names on macOS starting at 10.9.
[Pinned Libm source](https://github.com/apple-oss-distributions/Libm/tree/17a5f9daa3f5679f7536b26f133b40cc078753c3/Source) ·
[Apple builtin records](https://github.com/apple-oss-distributions/clang/blob/8204159ac8569f29fddc48862412243c2b79ce8c/src/tools/clang/include/clang/Basic/Builtins.def#L1192-L1194) ·
[LLVM deployment logic](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/lib/Analysis/TargetLibraryInfo.cpp#L516-L528)

The recipe adds the two declarations to the generated macOS dispatcher for
arm64 and x86_64 with C linkage and the macOS 10.9 availability annotation.

## Qualification

The [consumer fixture](../../.agents/skills/review-macos-c-sdk/scripts/sdk_review/headers/fixtures/c_interfaces/darwin_exp10.c)
checks both function types and verifies that a runtime argument of `3`
produces `1000` at both precisions. Clang 23.1.2 and Apple Clang 21.0.0
(`clang-2100.1.1.101`) gave these results.

| Probe | Result |
| --- | --- |
| C11 at macOS 14, arm64 and x86_64, with default, ANSI, POSIX and Darwin feature modes | The original generated header lacked both declarations. The repaired and Apple SDK headers compiled in all four modes. |
| C++17 at macOS 14, arm64 and x86_64 | The objects imported both functions with C linkage. |
| x86_64 at macOS 10.8 and 10.9 with `-Werror -Wunguarded-availability` | The repaired and Apple SDK headers rejected both calls at 10.8 and compiled at 10.9. |
| arm64 and x86_64 at O0 and O2 with `-fno-builtin` | `llvm-nm --undefined-only` showed both Darwin symbols. After linking against the Apple SDK, `dyld_info -imports` showed both through libSystem. |
| Executable fixture on macOS 26.5.2 (25F84) | Passed on native arm64 and Rosetta x86_64. |

Compile the fixture with Clang using
`-std=c11 -fno-builtin -nostdinc` and explicit `-isystem` paths for the
compiler's resource includes and the tested SDK's `usr/include`. Link the
object with Xcode's `clang -isysroot` using the Apple SDK, then run it with
`arch -arm64` or `arch -x86_64`.
