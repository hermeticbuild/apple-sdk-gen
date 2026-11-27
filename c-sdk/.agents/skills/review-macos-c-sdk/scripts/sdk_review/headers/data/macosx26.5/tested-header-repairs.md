# Tested macOS 26.5 header repairs

These results describe the historical repair experiments and their inputs.

This follows the [48-path ranking](ranked-header-differences.md). The installed
repairs use the Apple source lock for macOS 26.5. Xcode build 25F70 provided
comparison inputs. Runtime checks used macOS 26.5.2 build 25F84, native
arm64 and x86_64 under Rosetta. Deployment minima on link commands describe
linker behavior. They do not establish execution on historical OS builds.

## Installed repairs

| Interface | Changed recipe and proof |
|---|---|
| XNU symbol aliases | Use the selected AvailabilityVersions generator directory, also consumed by the availability headers. The unchanged Apple XNU script now emits all 78 macOS selectors. The 18 recovered selectors need no per-symbol exceptions. Each selector matched Xcode at five minima per CPU. Commit `6bd739e`. |
| `fpclassify` | For macOS arm64 C, build the binary64 part of the macro from Apple's pinned integer classifier. Float retains its original call. The reference and installed clients linked with our generated libSystem and ran for float, double and long double, at O0/O2 and minima 11.0/26.5 on both CPUs (48 executions). A signaling NaN returns the NaN category without setting FE_INVALID. The builtin-only candidate set that flag. Confirm the applicable redistribution notice for the C input in the release review. Commit `1d1e089`. [Producer and reference experiment](fpclassify-gap.md) |
| `CMPLX`, `CMPLXF`, `CMPLXL` | Keep the existing Clang constructor expressions. The 26.5 recipe enables them in C11 and later, and in full Darwin C for earlier dialects. All 16 tested C namespace/dialect combinations matched SDK visibility on both CPUs. Eight installed clients exercised initialization, signed zero, infinity, result types and single evaluation using GNU89, C89, C99 and C11 through our generated libSystem. Earlier SDK locks retain their original recipe. Commit `fe3638d`. |
| `AssertMacros.h` | Change Apple's guarded default to off. Explicit 1 enables the legacy names, explicit 0 disables them, and the prefixed macros remain available. The named-function collision, opt-in client and opt-out client matched the reference compile outcomes at 11.0 and 26.5 on both CPUs. Commit `fe3638d`. [Apple source](https://github.com/apple-oss-distributions/CarbonHeaders/blob/214a9ae7ab3c0c78ddb50328ca226e6313c4c782/AssertMacros.h) |
| `MacTypes.h` | Change the two no-argument callback typedefs to `(void)` in the 26.5 staging recipe. The valid client calling all three related types (including the alias) emitted byte-identical objects. Each negative one-argument client was rejected on both sides, both targets and both deployment minima. This is a reviewed derivation from CarbonHeaders-18.1. Commit `fe3638d`. |

A standalone C++17 include using only C and Clang resource headers exposes
the constructors in the reference C header and hides them in ours. An
earlier compiler-driver experiment with the C++ search paths enabled hid
them on both sides. The installed repair is qualified for C.

The final C tree has 767 header paths. Five header files changed relative
to the pre-repair C tree. Its header-manifest SHA-256 is
`00bb549ce554b3d321cb0473359e294f6cddd7176e21cfb45bb9652507347cc9`.
The 364 C compilation checks, 12 recipe tests and native fenv test passed.
The libSystem used for the strict links was the generated Libnotify candidate
with SHA-256 `8c35f896ddb7c0e34ba7dcb2c52644a5db2fa3cd2690497c28c77e3626f5e420`.

## Working prototypes and their release boundaries

| Interface | Concrete solution | Evidence still needed or decision |
|---|---|---|
| Modern `os/log.h` | Preserve XNU's object/type representation. Use Clang's OS log builtins to encode the format arguments, guard evaluation with the enabled predicate, and send the packed buffer through the userspace log sink. Link nine entries in the `libsystem_trace` child. Candidate/reference effective imports and format-string sections matched. Emission, disabled arguments, debug-on, privacy, sensitive formatting and diagnostics worked on both CPUs. | The current produced stub fails the nine imports. This prototype used a separate scratch stub. Obtain independent declaration evidence for the debug sink and disabled backing object, and qualify the deployment contract before release. The Swift call site establishes the generic packed sink. [Swift call site](https://github.com/swiftlang/swift/blob/swift-5.0-RELEASE/stdlib/public/SDK/os/os.m#L104) · [Swift API notes](https://github.com/swiftlang/swift/blob/swift-5.0-RELEASE/apinotes/os.apinotes) |
| Historical `os/trace.h` | Adapt the compiler encoding into the scalar value/size/count trailer documented in the pinned XNU header. The reference and prototype linked at 11/14/26.5 with three additional trace exports. Seven legacy trace events matched per CPU in the debug-enabled run. | Unmodified XNU calls two helpers absent from the current runtime. XPC payloads and standalone trace-base compatibility remain open. Preserve the experiment separately from the modern log path. [XNU trace interfaces](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/libkern/os/trace.h) |
| arm64 denormals environment | The prototype declares a const `fenv_t` named `_FE_DFL_DISABLE_DENORMS_ENV`, exposes its address as the macro and binds the data export in libsystem_m on arm64. It toggled hardware FZ, flushed input and output subnormals, and restored the prior environment. Intel kept its SSE interface. | **User decision: qualification only.** We have a macOS arm64 consumer, an Apple Libm engineer's account of the arm64 iOS spelling and the current macOS provider. Seek stronger macOS provenance before shipping either the declaration or the export. The [standalone qualification client](../../fixtures/c_codegen/fenv_denorms_environment.c) enables the proposed declaration only with `-DREVIEW_DERIVED_FENV`. Compile without it against the SDK control. [Client](https://github.com/breakfastquay/rubberband/blob/v1.9.2/src/system/sysutils.cpp#L185-L190) · [Engineer's account](https://stackoverflow.com/a/19904907) |
| Thirteen half-precision math imports | Install the LLVM-derived declarations and scan the resulting `math.h` to emit the 13 libsystem_m entries for both targets. The Apple Silicon, Rosetta and native Intel runtime images each show 0/13 in 14.7 and 13/13 strong in the initial 15.0 release. | SDK-identical client objects and results at 11.0/14.7/15.0/26.5. Runs used 26.5.2. On Rosetta the deployed `__rintf16(1.25)` returns 1.25 with either header. Historical and native Intel numerical behavior remain untested. [Inputs, image UUIDs and reproduction](../../../../../../../../recipes/libm/half_math.md) |
| `Block.h` | Installed follow-up in `2eb6abe`. Keep the licensed libdispatch input and derive pointer bounds for raw copy/release and the typed wrappers. The libclosure header still has an unresolved license placeholder. | Apple Clang accepts a single-pointer copy and diagnoses an unsafe raw release. Escaping-block objects matched the SDK at minima 11.0 and 26.5 on both CPUs, linked against the generated libSystem, and ran on 26.5.2 (Intel via Rosetta). [Derived recipe and regression](../../../../../../../../recipes/libdispatch/block-bounds.md) |

Scratch stubs and the reference SDK are outside the producer inputs.

### Modern logging follow-up

**Decision.** Keep modern logging in qualification. Preserve dedicated
error and fault calls as the release target. Seek independent evidence
for their six-argument prototypes and the supported deployment range.
The first-party Swift API notes name both functions. The published Swift
logging implementation sends debug messages through the generic packed
sink. [API notes](https://github.com/swiftlang/swift/blob/272c466e47507c4c6359f30ab8c9ceea5e7c216d/apinotes/os.apinotes#L31-L40) · [Swift debug implementation](https://github.com/swiftlang/swift/blob/d154f45f01cf339b4a01ac5dacc3fd3b1bb100fb/stdlib/private/OSLog/OSLog.swift#L56-L67)

The five-entry variant uses the generic sink for debug and preserves
the error/fault calls. Both CPUs, three deployment minima and two runtime
logging configurations gave 12 matching results for severity, message,
privacy redaction and disabled argument evaluation. All executions used
macOS 26.5.2. A separate Swift client verified that the public disabled
singleton's address equals the data export in libsystem_trace on native
arm64 and Rosetta x86_64. A null handle loses that identity. The dedicated
call signatures are inferred from the generic signature and successful
runtime calls. The legacy trace and XPC interfaces have separate gaps.
The five candidate linker names were also present in the native arm64e,
Rosetta x86_64 and native Intel x86_64h runtime images in both 14.7 and
15.0. These observations establish presence and leave the prototype decision
in place. Receipts are in `/tmp/half-release.EuT2mo/logging-results.md`.

## Other differences

- **Availability headers.** The real macro argument limit is **14 versus 16**. The suffixes 13 and 15 are zero-based. A scratch change to both dispatch generator methods matched the larger limit. The checked source corpus used at most seven arguments. Keep the pristine generator. Its existing version-check template operation can also diagnose mixed header sets, but a useful packaged check must distinguish build identities. The supplemented macOS numeric table already matches all 78 values.
- **Mach-O and libdispatch.** Keep the dyld image layout and cctools' historical platform alias. The public layout and modern loader client matched. A direct swap of the dispatch SPI annotation macro broke the source's workloop enum. Keep the paired source definitions. For ARM32 file inspection, LLVM's LLDB decoder supplies all 15 missing encoding constants and produced reference-identical decoder objects in scratch. Keep the existing deferral for 64-bit compilation. [LLDB decoder](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/lldb/source/Symbol/CompactUnwindInfo.cpp#L116-L137)
- **Target switches and legacy Carbon macros.** A scratch RTKit/watchOS definedness adjustment matched the reference while preserving the existing ABI switch. There is no demonstrated macOS consumer for those differences. Keep the current scope.
- **Thirty retained paths.** At six minima across both CPUs, 540 paired cells gave 384 byte-identical objects, 144 matching diagnostics and 12 expected slot-519 omissions. Each of the 30 paths had a compiled-client cell with its inclusion traced. All eight additional Apple Clang typed-malloc backdeployment checks passed. These runs used the first five-repair installation before a comment update in AssertMacros. The public interfaces are the same. [Path-by-path dispositions](ranked-header-differences.md)

The LLVM bootstrap, hermetic-llvm e2e and rules_rs suites have their own
release gate. Their earlier results apply to the previously qualified
composition.
