# macOS sine-pi declarations

The Libm input is `Libm-2026` at `17a5f9daa3f5679f7536b26f133b40cc078753c3`.
Its `Source/math.h` selects architecture headers that lack these two declarations.
The dispatcher adds them for macOS arm64 and x86_64.
[Pinned Libm source](https://github.com/apple-oss-distributions/Libm/tree/17a5f9daa3f5679f7536b26f133b40cc078753c3/Source)

Apple's open-source Clang at `8204159ac8569f29fddc48862412243c2b79ce8c` associates
`__sinpi` (type code `dd`) and `__sinpif` (type code `ff`) with `math.h`.
LLVM 23.1.2 at `85ac560262434c9ccfc0c183ec22d4138ed647fb` independently records
the signatures and enables the libcalls starting at macOS 10.9. The recipe uses
the existing Apple availability macro and C linkage for those interfaces.
[Apple builtin records](https://github.com/apple-oss-distributions/clang/blob/8204159ac8569f29fddc48862412243c2b79ce8c/src/tools/clang/include/clang/Basic/Builtins.def#L1181-L1185) ·
[LLVM signatures](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/include/llvm/Analysis/TargetLibraryInfo.td) ·
[LLVM deployment logic](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/lib/Analysis/TargetLibraryInfo.cpp)

The macOS 26.5 SDK (25F70) is the comparison reference. The generator uses
the pinned OSS Libm tree and this recipe. Recheck the declaration supplement
when the Libm pin changes or the reference surface changes.

## Qualification

The [sine-pi consumer](../../.agents/skills/review-macos-c-sdk/scripts/sdk_review/headers/fixtures/c_interfaces/darwin_sinpi.c)
checks both function types, signed zero at `-1`, and the exact result at `1.5`.
Clang 23.1.2 and Apple Clang 21.0.0 (`clang-2100.1.1.101`) gave these results.

| Probe | Result |
| --- | --- |
| C11 at macOS 14, arm64 and x86_64, with default, ANSI, POSIX and Darwin feature modes | Before the repair both declarations were undeclared. The repaired installation and reference compiled in all four modes. |
| x86_64 at macOS 10.8 and 10.9 with `-Werror -Wunguarded-availability` | The repaired installation and reference rejected both calls at 10.8 and compiled at 10.9. |
| arm64 and x86_64 objects at O0 and O2 with `-fno-builtin` | `llvm-nm --undefined-only` showed `___sinpi` and `___sinpif`. `dyld_info -imports` showed both through libSystem after linking with the reference SDK. |
| Executable fixture on macOS 26.5.2 (25F84) | Passed on native arm64 and Rosetta x86_64. |

For object checks, use the fixture with `-std=c11 -nostdinc` and explicit
`-isystem` paths for the compiler's resource includes and the tested tree's
`usr/include`. Link the resulting object with Xcode's `clang -isysroot`
using the reference SDK, then run it with `arch -arm64` or `arch -x86_64`.
