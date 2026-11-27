# macOS 26.5 C header differences, ranked for repair

This is the initial repair assessment. Use the current backlog for live
findings and the tested repair notes for subsequent changes.

Scope: the 48 installed paths with a byte-different counterpart in Xcode SDK
26.5 build 25F70. The inventory contains 715 other matching paths and four
installation-only paths. Missing SDK paths have a separate inventory. The
rank reflects impact on macOS arm64 and x86_64 C clients at deployment targets
from 11 through 26.5. Recommended dispositions are for review.

**Repair order.** The most consequential defect is a failed link from standard
C math on arm64. Modern logging also has a genuine userspace interface gap.
The first change I would actually land is the XNU symbol-alias generator input:
the fix uses the existing approved version table and the upstream generator
and is already proven in isolation. The cleanest source replacement is
`Block.h`, subject to resolving its license notice. Neither change depends
on solving the Libm or logging provenance gaps.

See the [tested repairs and prototype results](tested-header-repairs.md) for the subsequent implementation and the disposition of these recommendations.

## 1. Highest impact or a proven generator defect

| Header | What differs for a client | Recommendation |
|---|---|---|
| `math.h` | The Apple OSS umbrella selects architecture-specific Libm headers. On arm64, classifying a double or long double imports an unavailable helper. The reference links. The two headers also expose different extensions, including 13 half-precision entries missing in the installed-header linkage survey. The qualified scalar and paired trigonometric repairs are already in the installation. | Keep the ordinary-C failure first in the backlog. Search for an Apple OSS arm64 mapping, then qualify float, double and long double through compile, link and runtime. Keep the known failure explicit until that evidence exists. Track half-precision declarations separately, requiring signature, availability and provider per entry. [Source search and client links](fpclassify-gap.md) |
| `os/log.h` | The pinned XNU interface and the public userspace SDK interface differ in macro lowering, sensitive logging and external calls. Substituting the SDK header into our C installation fails on missing `os/trace.h` in all 12 cells. Nine logging names remain in the installed-header linker comparison. | Seek Apple's userspace logging header and install rule, including its trace dependency. Test emitted imports from actual logging calls, format handling and linkage. Keep the existing source gap open. An additional XNU kernel header or nine names added to a stub would leave the macro implementation unqualified. [Logging probe](../../c_interface_review.md#inspect-logging-macro-lowering) |
| `sys/_symbol_aliasing.h` | The installation has 60 macOS alias selectors. The SDK has 78. The public include route through `sys/cdefs.h` fails to compile a declaration/expression using the 26.5 selector on both CPUs. The XNU recipe reads the original DSL while the availability recipe reads the supplemented DSL. | Give Apple's unchanged `bsd/sys/make_symbol_aliasing.sh` the same staged DSL used for the other 26.5 headers. Record that input in provenance. Scratch regeneration supplied all 78 names and matched every macOS selector expansion across both CPUs at five minima. Keep the separate iOS-version differences outside this macOS repair. [XNU recipe](../../../../../../../../recipes/xnu/Makefile) · [Version supplement](../../../../../../../../recipes/availability_versions/macos-versions-26.5.patch) |

## 2. Concrete source or language-interface differences

| Header | What differs for a client | Recommendation |
|---|---|---|
| `Block.h` | Our header is the portable Blocks runtime copy from libdispatch. Apple ships the public libclosure header with bounds annotations and different copy/release wrappers. An ordinary C block-copy client produced identical objects. The distribution-pinned libclosure header matches the reference byte for byte. | Use libclosure's public Headers phase for this path. Its Xcode project identifies the public file and the install directory. Before redistributing it, resolve its literal license placeholder and record the applicable notice. Qualify copy/release and bounds-aware consumers. [Apple header](https://github.com/apple-oss-distributions/libclosure/blob/3668b0837f47be3cc1c404fb5e360f4ff178ca13/Block.h) · [Apple project](https://github.com/apple-oss-distributions/libclosure/blob/3668b0837f47be3cc1c404fb5e360f4ff178ca13/Blocks.xcodeproj/project.pbxproj) |
| `AssertMacros.h` | The older header defines short names by default. Declaring an ordinary function named `check` after inclusion fails on both CPUs and compiles with the SDK. Other changes include the assertion error value, C11 compile-time assertion, optional config include and control flow. | Prefer a newer licensed Apple implementation. The pinned XNU external copy also defaults the short names on. For the collision alone, CarbonHeaders already has the override and explicitly describes the intended next default. If a newer public copy remains unavailable, propose changing just the overrideable default, preserving opt-in, and test both modes. Audit the other macro behaviors separately. |
| `complex.h` | Our C11 constructors pass the existing C11 fixture. Darwin C99 code using `CMPLX` fails to compile here and compiles with the reference. The source and reference also differ in long-double compatibility machinery and declaration organization. | Keep the qualified builtin implementation. Prefer a newer Apple public header. Failing that, propose a source-backed change to its feature guard for Darwin C99, covering all three constructors, file-scope initialization, signed zero and strict ISO visibility. Verify long-double imports independently. |
| `fenv.h` | Layout and exception-mask repairs already pass their probes. The arm64 default environment for disabling denormals is still missing. The header difference also includes the organization of the architecture branches and macro spellings. | Keep the existing qualified environment and masks. Reopen the missing object only on independent declaration evidence. Then check its deployed provider, on-device denormal behavior and restoration of the original environment. Do not infer its contents from the reference object. |
| `MacTypes.h` | A C11 call through `ProcPtr` with one argument is accepted by our old-style unspecified-parameter declaration and rejected by the SDK's zero-argument prototype. Other differences include `StrLength` constness, `nil`, enum deprecation and legacy debugger declaration annotations. | Seek a newer public Carbon header. The indexed Apple OSS search for `ProcPtr` in this filename found the existing CarbonHeaders source. If necessary, propose narrowly sourced fixes for the callbacks first, then constness. Test valid zero-argument calls and rejection of invalid calls. |

## 3. Investigate when a consumer depends on the difference

| Header | What differs for a client | Recommendation |
|---|---|---|
| `Availability.h` | Public annotation dispatch supports more arguments in the SDK (16 arguments versus 14 in the installed macros, confirmed by compilation). Platform handling and mixed-header version checks differ. | Seek an updated Apple AvailabilityVersions generator and template as a unit. Exercise a real multi-platform declaration while compiling for macOS before adding a local template extension. |
| `AvailabilityInternal.h` | Generated argument dispatch, platform aliases and non-macOS version ceilings differ. The macOS ceiling and 26.5 macro have already been repaired. | Keep the tested macOS supplement. Update internals together with both public facades if an affected declaration is found. Do not transplant the generated reference file. |
| `os/availability.h` | The unprefixed annotation macros have the corresponding argument-count, platform and version-check differences. | Use the same upstream generator change as the two headers above, with a compile fixture through this public include path. |
| `AvailabilityVersions.h` | Additional other-platform version constants and a mixed-version guard appear in the reference. The current supplement supplies the macOS release constants. | Keep the Apple version generator and the reviewed macOS table. Check the complete macOS constant set at lock updates. Add other-platform constants only for a demonstrated macOS compilation requirement or a new platform scope. |
| `TargetConditionals.h` | The much larger reference supports many platforms. In ordinary macOS preprocessing the differences include missing `TARGET_OS_RTKIT`, an extra `TARGET_OS_WATCHOS` and textual spelling of the already validated per-CPU `TARGET_ABI_USES_IOS_VALUES`. Presence changes `#ifdef` behavior even when a macro would evaluate to zero. | Keep the macOS derivation and verify definedness as well as values for switches a client uses. Prefer a published Apple template update, and request evidence for each extra derived switch. Preserve the established ABI branch and the distinction between undefined and zero. |
| `mach-o/dyld_images.h` | The reference brings in unistd declarations transitively. Ours includes fixed-width integers and Mach definitions directly. Exclave handling for notification ports also differs. The existing macOS fixture checks size 368, alignment 16 and the ports offset 200. | Keep the layout checks. Prefer the public dyld install preprocessing if it can be reproduced. A downstream source relying on an incidental include can include its own dependency explicitly. Investigate new field or layout differences first. |
| `mach-o/loader.h` | The generated SDK and cctools use different preprocessor aliases for platform constants. The current paired `PLATFORM_MACCATALYST` feature test passes. Our source also exposes the historical `PLATFORM_IOSMAC` alias. | Retain cctools, probe definedness and integer values separately if a Mach-O reader depends on the old name, and compare XNU's external copy before considering a local change. |
| `dispatch/base.h` | The SDK removes internal build and Linux branches and changes `DISPATCH_ENUM_SPI_AVAILABLE` to an unavailable annotation. The macro definition differs in ordinary preprocessing. | Prefer the libdispatch public-header filtering rule if recoverable. Look for a shipped C enum using it and compare the diagnostic before changing the macro. |
| `ConditionalMacros.h` | The availability include, definition of `TYPE_BOOL` and historical architecture branches differ. Both installations report the same misleading long-double flag on arm64. Intel passes the existing check. | Keep the Apple source and document the shared limitation. A client deciding a C type's size can use the compiler. Reopen if the include or macro presence breaks a macOS consumer. |
| `mach-o/compact_unwind_encoding.h` | The SDK exposes additional 32-bit ARM compact-unwind encodings. Even a 64-bit analysis tool could use them when inspecting an ARM32 file. The focused mask probe fails on our installation. | Retain the agreed deferral for arm64 and x86_64 compilation. If foreign-file inspection becomes a requirement, seek the definitions from Apple or LLVM libunwind and validate a decoder fixture. |

## 4. Keep the upstream recipe for the tested macOS targets

These recommendations rely on the named client or the identified source
difference. They do not establish equivalence for other languages, Apple
platforms, compiler modes or every declaration in the containing header.

| Header | Difference and evidence | Recommendation |
|---|---|---|
| `malloc/malloc.h` | Two with-options functions have source availability 16.0 versus SDK 26.0. On both CPUs the pinned compiler diagnosed 26.0 below the threshold, accepted the untyped call at 26.0, and produced matching typed/untyped address-reference objects. Exclave guards are also filtered. | Keep Apple libmalloc. Retest imports and diagnostics at threshold on compiler updates. |
| `malloc/_malloc_type.h` | The 14.0 typed APIs differ in other-platform annotations. The previously repaired backdeployment switch controls actual imports on older targets. | Retain the source branch and the dedicated macOS 13/14 weak/strong import and fallback test. |
| `_stdlib.h` | The sole changed line gives `strtonum` availability as 10.16 versus 11.0. Address-reference objects matched in ten cells. | Keep the Libc public install. |
| `_string.h` | The same availability spelling differs on `strsignal_r`. Address-reference objects matched. | Keep the Libc public install. |
| `sys/_types/_fd_def.h` | The availability spelling changes on `__darwin_check_fd_set_overflow`. Objects matched through `sys/select.h`. | Keep the XNU definition. |
| `sys/uio.h` | The same spelling differs on `preadv` and `pwritev`. Objects referencing both matched. | Keep XNU, including its noncancelable naming rules. |
| `libproc.h` | Five process APIs carry the 10.16/11.0 spelling. A client referencing all five produced identical objects. | Keep XNU libproc. |
| `pthread/introspection.h` | The introspection get/set-specific APIs carry the older spelling. Objects matched for both. | Keep libpthread's public header. |
| `pthread.h` | JIT APIs differ in macOS version spelling and other-platform unavailability. Representative JIT references matched. | Keep libpthread's root install and qualify both include paths together. |
| `pthread/pthread.h` | The same JIT declaration differences appear in the nested include. The nested include probe also matched. | Keep the same libpthread source as the root install. |
| `pthread_spis.h` | The SDK drops a bridgeOS unavailability annotation on the legacy mutex-mode declaration. The macOS objects matched. | Keep libpthread's installed root path. |
| `pthread/pthread_spis.h` | The nested include has the same single annotation difference. Its own object probe matched. | Keep the libpthread source for both paths. |
| `os/workgroup_interval.h` | Three interval functions carry the older availability spelling. Start, update and finish references matched. | Keep the upstream public install. |
| `os/workgroup_object.h` | macOS availability spelling and other-platform SPI/unavailable annotations differ. Selected port, join and leave references matched. | Keep the public install. Recheck diagnostics if building for another OS. |
| `os/workgroup_parallel.h` | The parallel constructor uses the older availability spelling. Its reference matched. | Keep the upstream declaration. |
| `dispatch/workloop.h` | The installed header retains a libdispatch build-only type branch and the older availability on its workgroup setter. The public setter reference matched. | Keep the public libdispatch header. |
| `spawn.h` | Several SPI and other-platform availability attributes differ, as do 10.16/11 and newer version spellings. The paired addchdir availability diagnostic agrees, and selected spawn references matched. | Keep XNU's install. Retain explicit availability checks for newer APIs. |
| `gethostuuid.h` | iOS-family SPI versus unavailable annotations differ. The macOS introduction is 10.5 in both. Objects matched. | Keep XNU's public wrapper header. |
| `sys/unistd.h` | The SDK removes a bridgeOS annotation from `freadlink`. The macOS 13 introduction remains. Objects matched on both sides of the threshold. | Keep XNU. |
| `bsm/audit.h` | The audit deprecation macro uses 10.16 versus 11.0. A client using the macro received the same macOS 11.0 diagnostic. | Keep XNU's deprecation macro. |
| `bsm/audit_record.h` | Two audit deprecation macros carry the spelling difference. The 10.14-introduced variant also diagnosed deprecation at 11.0 on both sides. | Keep the pinned OpenBSM interfaces supplied by XNU. |
| `libkern/OSAtomicDeprecated.h` | FIFO enqueue/dequeue use 10.16 versus 11.0. Dequeue emitted the same deprecation diagnostic on both CPUs. | Keep libplatform. |
| `dlfcn.h` | The dyld source keeps a DriverKit SPI branch. The reference marks that use unavailable. The macOS `dlsym` object matched. | Keep the dyld source. |
| `mach-o/dyld.h` | Differences include ExclaveKit macro guards and bridgeOS annotations on the historical NS APIs. The public image-count reference matched. | Keep the dyld source and the existing preprocessing. Revisit specific deprecated APIs if a macOS diagnostic differs. |
| `sys/syscall.h` | XNU's generator leaves slot 519 unassigned. The SDK names a private syscall there. The generated source comment also differs. | Preserve the approved omission. Regenerate when Apple's public syscall master names the slot. |
| `dispatch/dispatch.h` | The public umbrella differs by a libdispatch-internal build guard. Identical preprocessed output and macro set in all 12 cells. | Keep upstream. |
| `dispatch/object.h` | A libdispatch build guard surrounds the differing region. All 12 cells matched. | Keep upstream. |
| `dispatch/queue.h` | Internal type branches, formatting and a visionOS availability spelling differ. All 12 ordinary client cells matched. | Keep upstream and qualify the public queue include through its umbrella. |
| `dispatch/time.h` | One availability invocation on `DISPATCH_WALLTIME_NOW` wraps across two lines. All 12 cells matched. | Keep upstream. |
| `sys/kdebug.h` | XNU retains explanatory comments on tracing constants. The client tokens and macro definitions matched in all 12 cells. | Keep the source with its comments. |

## Evidence and replay

The [linker census at 05d69d0](https://github.com/hermeticbuild/apple-oss-c-sdk/blob/05d69d063ccc4217644538095afff62fd299f5a5/tools/libsystem/progress.md) accounts for the 13
half-precision math names, nine logging names, and one arm64 environment
object. The header compilation survey below measures a separate property.

The [isolation procedure](../../c_interface_review.md) compares one changed
header at a time. It produced five equal paths, 42 with changed preprocessing
and one missing dependency. The input header-manifest SHA-256 is
`674576f8edda2cda7e75aecda4d3db1a1652722d86581c4b68cde6390c62f519`.

The follow-up object experiment compiled 23 C clients on both CPUs at 11.0,
13.0, 15.0, 26.0 and 26.5 with upstream Clang 23.1.2. Nineteen clients
produced byte-identical Mach-O objects in every cell. The other four were the
alias, C99 constructors, assertion name and legacy callback cases above.
The compiler saw one common sysroot for Mach-O metadata, used `-nostdinc`,
the pinned resource headers, and selected only the include tree under test.
Failing to pin that metadata changes `LC_BUILD_VERSION.sdk` in the objects.
The deprecation and availability diagnostics were tested separately with
warnings promoted to errors. These experiments concern compilation and
object contents. Link and runtime findings are cited individually above.

Three proposed changes also have scratch controls. Calling a function
named `check` with the upstream short-name switch set to zero, using the
regenerated XNU selector, and compiling a block-copy client with Apple's
libclosure header each produced reference-identical objects on both CPUs at
11.0 and 26.5. These tests establish the scope of those specific changes.
The libclosure source contains the literal `@APPLE_LLVM_LICENSE_HEADER@`
marker. The inspected tree at the 26.5 gitlink has no separately named
license file. Verify the applicable grant before switching the release input.

Representative reproductions, each in its own C translation unit:

```c
#include <sys/cdefs.h>
int alias_active(void) { return 0 __DARWIN_ALIAS_STARTING(__MAC_26_5, __IPHONE_17_0, +1); }
```

```c
#include <complex.h>  /* compile with -std=c99 -D_DARWIN_C_SOURCE */
double _Complex value = CMPLX(1., 2.);
```

```c
#include <AssertMacros.h>
int check(int value) { return value; }
```

```c
#include <MacTypes.h>  /* compile with -std=c11 */
long invoke(ProcPtr fn) { return fn(1); }
```

For the alias scratch trial, apply the approved version supplement
`recipes/availability_versions/macos-versions-26.5.patch` to a staged DSL. Expose the staged
`availability` and `availability.dsl` as `usr/local/libexec/availability.pl`
and `usr/local/libexec/availability.dsl` under an otherwise empty tool root,
and pass that root to Apple's `bsd/sys/make_symbol_aliasing.sh`. Include
the result through `sys/cdefs.h`. All 78 macOS selectors expanded identically
to the comparison header on both CPUs at 11.0, 14.4, 15.0, 26.0 and 26.5.

Reopen assessments on a source or reference digest change, compiler change,
new language/profile, or a counterexample within the supported targets.
