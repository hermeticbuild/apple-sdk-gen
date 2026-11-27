# Paired trigonometry in macOS math.h

Apple introduced `__sincos`, `__sincosf`, `__sincospi`, and `__sincospif` in
macOS 10.9 and iOS 7. The ordinary pair computes sine and cosine in radians.
The pi pair computes the results at π times its input using the runtime's
pi-specific argument reduction. The scalar pointer interfaces take the angle,
the sine destination, and the cosine destination in that order.
[Apple WWDC 2013 Session 713 slides](https://docs.huihoo.com/apple/wwdc/2013/session_713__accelerate_framework.pdf) ·
[HOOMD-blue Darwin call sites](https://github.com/glotzerlab/hoomd-blue/blob/b7fd93edbedcbacb18a75797e94b36a70fb2de9d/hoomd/HOOMDMath.h#L287-L330)

The `_stret` helpers take one scalar and return sine followed by cosine.
Darling's compatibility commit records the C struct tags `__float2` and
`__double2`, their `__sinval` and `__cosval` members, and all four helper
prototypes. The commit does not identify where the author learned the member
names. The generator uses these identifiers as compatibility facts and has
its own wrapper bodies. The runtime supplies all four paired operations,
including exact inputs such as `__sincospi(0.5, …)`.
[Darling's original compatibility commit](https://github.com/darlinghq/darling/commit/44f4440823a5ce72eb1f6f2ae956a2532b4c7416)

LLVM 23.1.2 independently defines both ordinary helper signatures and the
pi pair lowering. On arm64 the results occupy `s0`/`s1` for float or `d0`/`d1`
for double. On x86_64 the float pair shares the low two lanes of `xmm0`, while
the double pair occupies `xmm0`/`xmm1`. C aggregate returns produce the correct
ABI on both architectures without architecture-specific declarations.
[LLVM ordinary signatures](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/lib/IR/RuntimeLibcalls.cpp#L180-L220) ·
[LLVM pi pair ABI and element order](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/lib/Transforms/Utils/SimplifyLibCalls.cpp#L2940-L2988)

Below macOS 10.9 the generated header implements the ordinary pointer pair
with separate `sin` and `cos` calls, or their float equivalents. A pinned LLVM
test independently demonstrates the same fallback for compiler-generated
calls. The pi wrappers and the four `_stret` declarations require 10.9 or
newer. The generator uses the shipped Apple OSS XNU inline macro so it
preserves Darwin's C and C++ linkage behavior. The generated block is scoped
to arm64 and x86_64 macOS and is available in strict C, GNU C, and C++ modes.
[LLVM macOS fallback test](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/test/CodeGen/X86/isel-llvm.sincos.ll#L122-L139) ·
[LLVM pi availability predicate](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/lib/Analysis/TargetLibraryInfo.cpp#L38-L54) ·
[Apple OSS XNU inline macro](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/sys/cdefs.h#L364-L423)

The installed-header fixture tests the struct layouts and the ordinary and
pi wrappers. Compile it with `-DTAKE_PAIRED_TRIG_ADDRESSES` to exercise
address-taking. At `-O0`, direct calls import the four `_stret` exports on
supported targets. C address-taking imports the four external pointer
functions. C++ address-taking materializes the inline functions and imports
the four helpers. Both sets resolve through `libSystem` to `libsystem_m` on
the observed macOS 26.5.2 host's arm64e and Rosetta x86_64 runtime images.

The Xcode 26.5 comparison was a separate read-only check. It matched the
candidate's symbol imports and deployment boundary. Its modern header
exposes the wrappers even in pre-C11 and explicitly POSIX or ANSI modes.
The x86_64 macOS 10.8 direct-call fallback was verified in objects. The runtime
checks ran on macOS 26.5.2.
