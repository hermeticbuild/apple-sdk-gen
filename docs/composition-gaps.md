# Qualify SDK Gen composition inputs

Use this evidence when a framework or stub from a new SDK Gen release changes. Check the result against the [consumer profile](../tools/sdk_composition/README.md#consumer-archive).

The [framework recipes](../frameworks/README.md) reproduce the
qualified CoreFoundation and audio framework replacements. Each directory
records its own provenance. The stock 27.0 CoreFoundation and AudioToolbox
umbrellas fail the C include checks for this composition.

For consumer qualification with SDK Gen 0.0.4, restrict `___divsc3`,
`___divdc3` and `___divxc3` to `x86_64-macos` in the
`/usr/lib/system/libcompiler_rt.dylib` document inside `usr/lib/libSystem.B.tbd`.
Apply this correction to a local SDK Gen input before composing. Runtime
symbol lookup on macOS 26.5.2 found all three on Intel and none on arm64,
which agrees with the SDK 26.5 target groups. The hermetic-llvm
`libomp_test` exercises the arm64 fallback to LLVM's static builtins.

Use `make -C frameworks test` on a new composition to run each replacement
framework's compile or link probe on both architectures. Audit any new
declaration or export against its own documented inputs.

## Expanded public framework composition

The [expanded composition](../tools/sdk_composition/README.md#expanded-framework-trial)
imports SDK Gen 0.0.5's 270 top-level frameworks and adds the local Cocoa
and ApplicationServices bundles. Prepared recipes supply the qualified
frameworks. Path overlays preserve generated assets in CoreServices and
Security. The trial retains the qualified SDK Gen 0.0.4 libSystem and
the existing standalone stubs.

The first expanded trial with the Security overlay produced the same
archive twice. Its SHA-256 was
`c573e42bea0f697c1205221394c8f9d40fe547ed7e09752d23d70cfe09509207`.
The installed framework probes and the DNS-SD, resolver, Foundation
macros, and Security API probes passed on arm64 and x86_64. The missing
framework paths and generated header failures below remain open.

`@llvm//tools:clang` with `stage1_from_source` built against the expanded
tree on the remote lane for both architectures. c-ares and curl passed
locally on both CPUs. Curl also passed with its default TLS configuration,
which links Security.

[Arm64 Stage 1](https://app.buildbuddy.io/invocation/ee673ad7-e09e-4bd4-9088-af33f5d1726c)
· [Intel Stage 1](https://app.buildbuddy.io/invocation/5b3acf46-718b-47a5-ac85-7e890e3208be)

| Consumer requirement | Result |
| --- | --- |
| Missing framework stubs | SDK Gen 0.0.5 supplies 26 of the 30 requested names, including Network and ModelIO. The ApplicationServices recipe adds a 27th. Carbon, OpenGL, and private FontServices remain open. |
| Foundation macros | The Foundation recipe delegates the enum, options, and nullability macros to the installed CoreFoundation macros. The composed probe compiles, links, and runs on both CPUs. |
| CoreGraphics | Regenerated with SDK Gen PRs #17–#19. The umbrella compiles as C and Objective-C. Color, geometry layout, and affine-transform probes compile, link, and run on both CPUs. Other enum values and API coverage remain open. |
| Security | Apple's 26.5 public umbrella compiles as C and Objective-C. A modular Objective-C++ include compiles and a Security API call runs on both CPUs with SDK Gen's stub. |
| Network | Regenerated with SDK Gen PRs #17–#19. The umbrella compiles as C and Objective-C, and endpoint probes compile, link, and run on both CPUs. The generator preserves documented enum storage types and omits constants without value evidence. |
| AVRouting | SDK Gen lacks `AVCustomDeviceRoute.h`. Apple ships the header on macOS and marks the class unavailable there. DocC lists iOS, iPadOS, Mac Catalyst and visionOS for the class. Header availability and API availability need to be represented separately. |
| ModelIO and MetalKit | MetalKit lacks the historical `MTKModel.h` header path. The generated ModelIO umbrella also needs SIMD. SIMD remains deferred. |

[SDK Gen PR #17](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/17)
· [SDK Gen PR #18](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/18)
· [SDK Gen PR #19](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/19)
· [AVCustomDeviceRoute DocC](https://developer.apple.com/tutorials/data/documentation/avrouting/avcustomdeviceroute.json)

The macOS SDK preview workflow from SDK Gen PR #13 landed on the manual
release feature branch after that branch merged. The default branch
therefore has no callable preview. A local restoration on
`cerisier/restore-macos-preview` also accepts an SDK version. GitHub
rejected pushing the workflow with the current OAuth credential because
it lacks `workflow` scope. A local macOS 26.5 crawl of the six reported
frameworks used the merged source and the header fixes from PRs #17 and
#18 for diagnostics.

### Regenerated CoreGraphics and Network

Regenerated macOS 26.5 from the DocC cache with upstream PRs #16–#19
applied. The combined generator revision is `6d0e294`. The two
generated bundles replace the raw SDK Gen copies in the trial
composition under `build/cg-network.jHtKBh/qualified.sdk`.

The existing `test-coregraphics` and `test-network` probes linked and ran
with the composed SDK on arm64 and x86_64. C11 probes also matched the
Xcode 26.5 reference on both CPUs for the geometry layouts, a rotated
rectangle's bounding box, the Network endpoint handle and Ethernet
address types, and a socket-address endpoint. Mach-O imports confirm the
geometry and endpoint calls bind through their respective frameworks.

The installed macOS runtime supplies the exported geometry and affine
transform functions on both CPUs. The generator keeps inline bodies for
the four constructors it could not find in either runtime slice and
omits those constructors from the stub exports. Apple places the C
geometry records under its CoreFoundation documentation. The regenerated
Network umbrella no longer redeclares Security exports.

[CoreGraphics geometry topics](https://developer.apple.com/documentation/coregraphics/cggeometry)
· [CGAffineTransform components](https://developer.apple.com/documentation/corefoundation/cgaffinetransformcomponents)
· [Network enum documentation](https://developer.apple.com/documentation/network/nw_interface_type_t)
· [Opaque C and Objective-C declaration changes](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/19)

The probes cover the named client calls and record layouts. Network
enumerators whose values DocC omits remain a source gap, and the other
CoreGraphics enum values still need independent verification. SDK Gen
received HTTP 403 for a cross-linked `expm1` DocC page during the crawl.
SIMD remains deferred.

### Local replay before merging

Replayed SDK Gen PRs #16, #17, #18, and #19 in that order from
`ca40c02`. The existing #19 head conflicted with the combined enum
export, C declaration, and callback fixes. The local restack tip
`3b47e92` has the same Git tree as the qualified `6d0e294` build.
The four branch tips passed 12, 14, 15, and 18 unit tests using the
upstream CI commands on native x86_64 Ubuntu 25.04 and in an x86_64
Ubuntu 24.04 container. Both used Python 3.12. The fresh macOS probes
ran on Apple Silicon, with the x86_64 binaries running through Rosetta.

A fresh, macOS-only regeneration produced byte-identical CoreGraphics
and Network bundles. The expanded SDK passed 34 framework recipe checks,
12 composed SDK checks, and four C ABI probes across arm64 and x86_64.
Two writes of the archive produced SHA-256
`fac8077b1a2276decbe7cefcb8e50ccd2706cf96b67120939568cf68dcc1e51d`.
The Stage 1, hermetic-llvm, and rules_rs results below apply to the prior
archive.

Regenerating AVRouting, ModelIO, and MetalKit with the same stack still
leaves three failing probes on both CPUs. AVRouting and MetalKit still
lack `AVCustomDeviceRoute.h` and `MTKModel.h` respectively. Regenerating
ModelIO clears the old C linkage macro error. Its first remaining error
is a generated import of `ObjectiveC/ObjectiveC.h`. The same umbrella
also requests `kernel/kernel.h` and `simd/simd.h`. Check the origin of
the Objective-C and kernel imports before extending the SIMD scope.

#### SIMD headers for ModelIO

The reported probe independently declared all 14 SIMD types used by the
generated ModelIO umbrella. With pinned Clang, the declarations matched
Xcode 26.5 on arm64 and x86_64 for size, alignment, field offsets and
by-value calling conventions. For example, `vector_float3` has 16-byte
size and alignment. Re-run the probe from the SDK repository when
qualifying the generated headers.

SDK Gen now reads the vector declarations, the matrix `columns[4]`
members, the quaternion `vector` members and the aliases from the public
C-family DocC pages. It installs `usr/include/simd/simd.h` and a Clang
module map. The composer selects those two files from the framework input.
The Model I/O emitter routes both SIMD topics and the Kernel-indexed
`vector_int2` and `vector_int4` aliases to that header.

The arm64 test compiles and runs against the composition. Clang emits the
same by-value function signatures as it does with Xcode 26.5 for all 14
types. The checked-in probe also compares sizes, alignments and record
member offsets. Objective-C++ inclusion and Objective-C `@import simd`
both pass. [SIMD ABI fixture](../tests/minimal_sdk_linking/simd-abi.c)

SDK Gen now emits a class after its same-framework superclass, using
the superclass from the rendered Objective-C declaration. The Foundation
recipe carries a [patch for the voice overlay](../frameworks/Foundation/voice-array-generics.patch)
that preserves the element parameter of `NSMutableArray`. Regenerating
Model I/O from 962 cached DocC symbols and composing both changes passes
the arm64 Objective-C import, link and runtime test. After regenerating
CoreGraphics with the fixes below, the arm64 Objective-C++ module probe
also compiles, links and runs.

[Clang extended vectors](https://clang.llvm.org/docs/LanguageExtensions.html#vectors-and-extended-vectors)
· [Apple SIMD documentation](https://developer.apple.com/documentation/simd)
· [Matrix members](https://developer.apple.com/documentation/simd/simd_float4x4)
· [Quaternion members](https://developer.apple.com/documentation/simd/simd_quatf)

#### OpenCV macOS wheel after SIMD

A standalone reproducer is available as `socat-opencv-sdk-repro.tar.gz`
for the wheel workspace's
`opencv//:ocv.3rdparty.avfoundation` and
`opencv//:ocv.3rdparty.cocoa` targets. Bazel 9.3.3 on Linux x86_64
reproduced both failures for the exact `fac8077b1a22…` archive, targeting
arm64 macOS. AVFoundation reached CoreGraphics callbacks with `_Bool`
and five uninitialized constants. The old Metal header imported
`Dispatch/Dispatch.h`. Cocoa hit missing Foundation and AppKit APIs
including `NSMutableDictionary`, `NSImage` and `NSSlider`.

SDK Gen now renders the callback type with `bool`, keeps
`CGBitmapInfo` as a `uint32_t` bitmask, initializes the five constants,
and leaves static declarations out of the stub. Pinned Clang emitted
the same 17 bitmap and glyph constant values as Xcode 26.5. The CoreGraphics
stub lost six false exports, all absent from the reference stub.
[CoreGraphics provenance](../frameworks/CoreGraphics/provenance.md)

The second Bazel run used a diagnostic copy of the exact archive with
the regenerated CoreGraphics header and lower-case dispatch imports,
matching the current generator's import spelling. The AVFoundation
compile cleared both errors and stopped when Metal pulled in DriverKit,
whose generated header imports the nonexistent `kernel/kernel.h`.
The Cocoa errors remain. Neither backend passed this run.

Metal’s `setOwnerWithIdentity:` DocC entry points `kern_return_t` to
DriverKit and `task_id_token_t` to Kernel. SDK Gen now maps them to the
public XNU `mach/kern_return.h` and `mach/mach_types.h` headers.
Regenerated Metal keeps the method and removes both framework imports.
With that header in the original archive, OpenCV then reached incomplete
`MTLPackedFloat3` and `MTLPackedFloat4x3` records and CoreVideo’s
`OpenGLES/OpenGLES.h` import. Record both as SDK Gen gaps.

The local Cocoa and media recipes now develop separate public surfaces
from the documented APIs and link names. Foundation and AppKit preserve
the earlier voice declarations. CoreVideo, CoreMedia, AVFoundation, and
QuartzCore have their own headers, InstallAPI commands, provenance and
arm64 runtime probes. The earlier exact archive remains the build
comparison input.

Bazel 9.3.3 on Linux builds both unchanged backend targets with
`--@llvm//config:macos_libcxx_headers=sdk`. This uses the archive's
LLVM 21.1.6 libc++ headers. The first executable link then reported
three missing compiler-generated objc4 imports. SDK Gen's 26.5
`libobjc.A.tbd` gained `objc_msgSendSuper2`, `objc_getProperty`, and
`objc_setProperty_atomic` after verification against Apple's pinned
objc4 sources and the installed macOS dylib. The
[property fixture](../tests/full_sdk_frameworks/objc-property.m) checks
all three through an atomic retained property and a superclass call.

Archive `aa9a370cd0e7a0c8ab6f29e29d0cbf203d1956728c3e1688fe6165381cc8baa9`
builds both backends and links the OpenCV highgui and videoio executable.
The resulting arm64 binary writes a three-frame MJPEG QuickTime file
on macOS and reads back all three frames through AVFoundation. The
local Cocoa tests run the image, collection, and event calls without
opening a window. Two writes of the archive are byte-identical. The
monorepo wheel and Codex Desktop are outside this reproducer.

After the OpenCV backends pass, audit every local framework and
composition recipe against a fresh matching macOS SDK Gen build. Include
its patches, replacement headers, install-name and reexport corrections,
and prepared framework bundles. For each, record the failing generated
input, its provenance and regression probe, and decide whether SDK Gen
should generate it, the recipe should continue to take it from Apple OSS,
or the workaround can be removed. Track the corresponding upstream changes
and retire each local override after the regenerated inputs pass its probe.

### Match Darwin stubs to the 26.5 source lock

[SDK Gen PR #20](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/20)
requires versioned Darwin metadata for 26.5 and preserves the supplied
export and reexport target groups. The bundled 27.0 stubs are byte
identical to the prior generator on every configured platform.

On arm64 and x86_64, strict links to `pipe2` and `dup3` succeed against
the previously bundled data and fail with the matching undefined-symbol
diagnostic against both Xcode 26.5 and the local regenerated stubs. A
`pipe` client links and runs on both CPUs. Neither newer name appears
in the locked XNU syscall definitions or userspace syscall sources.

The two local SDK Gen invocations used a 26.5 inventory from Xcode as a
comparison input. That file stays local. A distributable same-version
composition still needs a reviewed Darwin inventory and a macOS-only
framework preview from the DocC cache at 26.5. Use the C and objc4
source locks for headers. The earlier standalone libSystem recipes
survive in the local archive. Their final component lock and tested
outputs were in scratch and are unavailable at the recorded paths.
Port or reconstruct the needed source-backed evidence before pinning
the new SDK Gen input. Then replay the voice native prefix and runtime
on both CPUs.

The composer now checks both SDK Gen roots and the C and objc4 source
locks before planning the install. The previous 27.0 input is accepted
only for the existing exact-asset consumer archive replay. The test
against the real 27.0 release failed at version selection before opening
the header manifest or creating an output directory.

A local 26.5 composition combined PR #20 with the qualified framework
stack at `62f5e65`. SDK Gen generated CoreGraphics, Network, and
Security for 26.5. The composer used the Apple OSS Security overlay,
CoreFoundation and SystemConfiguration recipes, and the pinned header
installations. DNS-SD, resolver, CoreGraphics, Network, Security,
CoreFoundation and SystemConfiguration probes passed on both CPUs.
The initial, smaller preview established that Network still needs the
Security bundle. The passing preview includes it. The Darwin inventory
in this experiment came from the local Xcode reference. Replace it
with the regenerated, reviewed inventory in a separate SDK Gen data PR
before distributing a new composition.

### Rebuilt source-backed iteration

The working tree under `build/darwin-inventory-26.5.kUsWl8` exercises
all four SDK Gen Darwin libraries without using the installed SDK as
a generation input. It uses the pinned macOS 26.5 C headers, the
Libsystem component graph, the reviewed Apple Libc, XNU, dyld,
libunwind, CommonCrypto and Libnotify recipes, and verifies providers
on the matching arm64e and Rosetta x86_64 runtime images. The libSystem
conversion runs LLVM's TBD transform once per inlined library and
checks all 40 documents after recombining. Merging the two whole
architecture files dropped the child documents in the first experiment.

The objc4 public header scan supplies the user API. The compiler ABI
adds 22 names per target from pinned Apple declarations and Clang's
code generation and ARC documentation after verifying deployed
exports. The libc++ and libc++abi candidates start from LLVM 23.1.2's
Darwin ABI lists and export lists, then retain the definitions and
symbol reexports confirmed on the corresponding macOS 26.5.2 runtime.
The comparison found zero candidate-only names across all four
Darwin libraries. Reference-only names remain open. The scope and
sources for the versioned preview are recorded in
[SDK Gen PR #21](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/21),
which depends on
[SDK Gen PR #20](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/20).

The local archive is
`build/darwin-inventory-26.5.kUsWl8/broad-ctype/MacOSX.sdk.tar.zst`
at SHA-256
`1417b7ef6dcb61326c7185224730f1c9652e21b08c144a1af9475fa511c49e8b`.
The C, Objective-C ARC and C++ smoke binaries ran on both client
architectures after archive extraction. Both extracted target stubs
rejected links to `pipe2` and `dup3`. DNS-SD, resolver, CoreGraphics,
Network, Security, CoreFoundation and SystemConfiguration passed their
composed probes. This is a local iteration artifact. The linked export
coverage and native voice replay are tracked in
[the Codex consumer check](codex-consumer-check.md).

### Legacy frameworks still missing

| Framework | Evidence and next qualification |
| --- | --- |
| OpenGL | The pinned Khronos registry at `6af574a14089ccfee87efe230ebcdd8742859813` supplies 858 candidate commands through desktop GL 4.1. Both macOS 26.5.2 slices provide 828 of them in libGL. Both runtime slices confirm the umbrella's libGL and libGLU reexports. A small stub for the independently declared `glGetError` linked and ran on both CPUs. The remaining GL commands, Apple CGL, and GLU still need release evidence. |
| Carbon | Apple OSS CarbonHeaders supplies common Darwin headers. Xcode 26.5's Carbon framework is a separate umbrella with children such as HIToolbox and OpenScripting. Use an identified child API to qualify the first reexport and header path. |
| FontServices | The reference stub lives under PrivateFrameworks and there is no header bundle at that path. Keep the gap recorded and check the actual private install name and symbol if a consumer link requires it. |

[Pinned Khronos GL registry](https://github.com/KhronosGroup/OpenGL-Registry/blob/6af574a14089ccfee87efe230ebcdd8742859813/xml/gl.xml)
· [Apple OSS CarbonHeaders](https://github.com/apple-oss-distributions/CarbonHeaders)

The Codex workspace's SDK selection lists OpenGL and FontServices.
The examined voice build disables the GStreamer GL plugin group and
the packaged macOS runtime's allowed system imports name neither
framework nor Carbon. Confirm actual framework use from the native
prefix link actions as the voice build advances. Archive selection is
a separate check for these two workspace-level requests.

### Security source closure

Apple's pinned 26.5 Security source supplies the umbrella and its
76-header Security include closure. After the CoreFoundation macro
repairs, the remaining dependencies are `xpc_object_t` in `SecCode.h`,
`CF_CLOSED_ENUM` in `SecureTransport.h`, and the two XNU libDER headers
used by `oids.h`.

Apple's BSD-licensed WebKit compatibility header in the matching 26.5
distribution supplies both forms of `xpc_object_t`. It uses libdispatch's
object macro with Objective-C and a void pointer in C. Both forms match
the Xcode 26.5 type checks on arm64 and x86_64. No Apple OSS libxpc
project or public umbrella was found. The older jceel header carries
Apple's all-rights-reserved notice. Darling publishes its own GPL-3.0-or-later
header. Neither is a recipe input.

The approved standalone C recipes install `xpc/_xpc_object.h` for the object
type and `libDER/DERItem.h` plus `libDER/libDER_config.h` from pinned XNU.
The XPC client API remains open. The libDER receipt identifies the XNU
path and the missing upstream public install rule. The C install passed
386 compile checks and the fenv runtime probe. The SDK path review
reported zero installed files without provenance. Its one required SDK
path absent from the stand-alone install is `tgmath.h`, supplied by the
pinned Clang resource directory in the successful C compile checks.

The Security overlay stages the verified Apple OSS source closure and
keeps the SDK Gen linker stub. It takes `CF_CLOSED_ENUM` from pinned
Swift Corelibs Foundation through the CoreFoundation recipe. An
overlay keeps the source filename when DocC changed its case, as with
`cssmaci.h`. The consumer test calls `SecCopyErrorMessageString` and
passes for arm64 and x86_64.

The exact-archive hermetic-llvm runs found an additional boundary on
arm64 and x86_64.
ThreadSanitizer uses `__has_include(<xpc/xpc.h>)` to enable its XPC
interceptors. The object-type-only umbrella enabled that code without
declaring `xpc_connection_t` or `xpc_handler_t`, and the runtime build
failed. Intel rules_rs passed all 39 tests. A diagnostic copy exposes
the same type at `xpc/_xpc_object.h` and uses it as the fallback in
Security's staged `SecCode.h`. C and Objective-C include probes passed
on both CPUs with the public XPC umbrella absent. The pinned
hermetic-llvm workspace also built `//:tsan_fail` for both CPUs with
the alternate layout. The checked-in recipe uses that layout.

The corrected composition SHA-256 is
`e75fa8ef968e574cb0eef77ecd94ce8876d64b40c923d762b261cc7ef7298e6f`.
The SDK payload changes are the relocated type and the staged
`SecCode.h` include. The C fixture reproduced the false discovery
on both CPUs with the previous installation and passed with the new
one. The new composition also passed the Security, DNS-SD, resolver,
Foundation macro, and framework recipe checks on both CPUs.

Two independent compositions produced that same archive. The remote
Stage 1 `@llvm//tools:clang` builds produced arm64 and x86_64 Mach-O
executables. Both local hermetic-llvm runs passed 38 tests each, with
45 skipped per architecture, and built the TSan target. The local
c-ares and default TLS curl tests passed on both CPUs.

The pinned rules_rs test workspace passed all 39 tests on each CPU.
The replay used Bazel 9.3.1 and the same SDK projection as the other
checks. The local SSH agent could not sign the public Serde fetch.
The direct workspace replay passed a temporary Git config through
`--repo_env=GIT_CONFIG_GLOBAL=...` to fetch the same pinned commit
over HTTPS. The integration wrapper and user Git config stayed untouched.

[Arm64 Stage 1](https://app.buildbuddy.io/invocation/3679715e-08a0-43f0-83e0-e6462329d065)
· [Intel Stage 1](https://app.buildbuddy.io/invocation/fc42d2b4-26b4-47ec-942f-b0b88608d56a)

[Apple OSS Security umbrella](https://github.com/apple-oss-distributions/Security/blob/97c3a4296c1ea06b0fe1877a7e616aa84450b5b2/base/Security.h)
· [Pinned WebKit type fallback](https://github.com/apple-oss-distributions/WebKit/blob/2a36545bf8dd89a417b724184900270fb2f523aa/Source/WTF/wtf/spi/darwin/XPCSPI.h)
· [Pinned XNU libDER headers](https://github.com/apple-oss-distributions/xnu/tree/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/EXTERNAL_HEADERS/libDER)

## Arm64 macOS 26.5 SDK Gen fork

The fork ports the twelve SDK Gen changes for C and Objective-C framework
generation and the versioned Darwin inventory. The comparison baseline
at `817afcc` passed remote Stage 1 Clang, the local LLVM and rules_rs
suites, the Codex voice host including runtime relocation, and the
c-ares and curl consumers. Its archive SHA-256 is
`35096a24d6b350c18f00a2c344e7e6f7537b9cbd9b128471ccb7edc386e24316`.
[Stage 1 baseline](https://app.buildbuddy.io/invocation/8e9e2063-0094-4a89-aab5-8e9cdf638426)

Both compositions use the fork’s LLVM 21.1.6 header install and the
`macos_libcxx_headers=sdk` consumer setting. Xcode 26.5 reports the same
libc++ version, ABI namespace, and vendor availability setting. The two
header sets produce the same imports for the C++ exception and RTTI
probe with the same compiler. Of 1,680 shared paths, 1,651 are
byte-identical. Xcode has five additional paths. The pinned release
provides the tested C++ surface, with Apple’s additional header changes
remaining a separate parity question.
The sanitizer links exposed four missing direct libc++abi exports.
Adding LLVM’s Darwin export list to the 26.5 arm64 inventory resolved
both links. The audited runtime supplies the library at
`/usr/lib/libc++abi.dylib`.
[LLVM Darwin export list](https://github.com/llvm/llvm-project/blob/a832a5222e489298337fbb5876f8dcaf072c5cca/libcxxabi/lib/symbols-not-reexported.exp)

The arm64-only generator retains relevant Swift-language DocC
declarations for C and Objective-C rendering. The composition uses the
source-locked C and objc4 layers and the prepared Foundation, AppKit,
Core Data, and Cocoa layers. Apply the Foundation voice module-map patch
when replaying that preparation. The framework gate exercises the
audio, security, network, graphics, CoreServices, and ApplicationServices
surfaces used by the selected clients. The wider AVRouting, Model I/O,
and MetalKit probes remain open with the SIMD work.

The arm64-only archive SHA-256 is
`f9dd6c4c2122c8dfd5cea70b25014a34413ad409fe5319be427b8b5e683328d4`.
Repacking reproduced the digest. All 16,026 C-family headers and module
maps match the baseline bytes. All 32 stub files target arm64 macOS,
and their retained exports, reexports and provider names match the
baseline arm64 surface.

The trimmed archive passed remote Stage 1 Clang, 34 applicable local
hermetic-llvm tests and the LCOV report check, all 39 rules_rs tests,
all four Codex voice test targets, the framework link probes, and the
c-ares and curl tests. The consumer suites ran directly in their
pinned upstream Bazel workspaces. The native voice test exercised
one relocated runtime case. The same archive is available at
`build/sdk/MacOSX.sdk.tar.zst`. [Trimmed Stage 1](https://app.buildbuddy.io/invocation/e8f83229-07ec-46b2-9b38-992983e8e4d5)
