# Codex consumer check

The Codex checkout was detached at
`56bb44c05c9b2056642ed356cf847f004519cc95`. Bazel 9.3.3 used a
repository override containing the unpacked macOS 26.5 SDK from
`cb5c723`. The archive SHA-256 is
`4b8bec003afa00e4612d512423790420fa231067f03dc44ec542c95ce5502cbd`.
The override adds the SDK package's Bazel metadata from the corresponding
hermetic-llvm commit.

## Initial build

Bazel analyzed ansi-escape, keyring-store, sandboxing, realtime-webrtc,
the voice host, and the CLI on arm64. When executing those targets, the
pinned LLVM toolchain at `d27493f0386c9d4d28f7b12630cb91b0cdfd20f1`
could not find `cerrno` in the rules_rust process wrapper or `memory` in
AWS-LC. Xcode 26.5 supplies the C++ headers in the SDK location that
this pin expects. The build was stopped after capturing both compiler errors.

The second pass uses the previously qualified hermetic-llvm commit
`190fc9f5df9c86ed0f1db77e408381f427dcb829` and
`--@llvm//config:macos_libcxx_headers=llvm`. Both overrides are command
line options for the experiment. The SDK archive and Codex sources stay
on their recorded revisions.
[hermetic-llvm PR #978](https://github.com/hermeticbuild/hermetic-llvm/pull/978)

The arm64 ansi-escape and realtime-webrtc test binaries built with this
toolchain and the exact archive. The keyring and sandboxing binaries and
the CLI's schema generator reached the framework link failures below.
The voice host also depends on the failing pkg-config build.

The next pass uses a local diagnostic copy of the SDK repository. It
adds the two existing SDK Gen stubs and removes the two exact
`_pipe2` export rows. The resulting tree serves only the Codex
experiment. The source package, committed composition, and qualified SDK
archive retain their original contents.

## Focused targets

All four suites pass with the diagnostic copy on arm64 and x86_64. The
Intel binaries ran locally under Rosetta.

| Bazel target | SDK surface exercised |
|---|---|
| `//codex-rs/ansi-escape:ansi-escape-unit-tests` | Rust test binary and libSystem linkage |
| `//codex-rs/keyring-store:keyring-store-unit-tests` | Security and its error-message API |
| `//codex-rs/realtime-webrtc:realtime-webrtc-unit-tests` | Rust session implementation |
| `//codex-rs/sandboxing:sandboxing-unit-tests` | CFNetwork and Security linkage, libSystem's Seatbelt exports |

Inspecting the arm64 sandboxing executable confirms that Security supplies the
trust-settings and certificate imports, and libSystem supplies
`sandbox_check`. For local x86_64 tests on Apple Silicon, Bazel also
needs the Intel execution platform:

```sh
bazel --nohome_rc test \
  --override_module="llvm=$LLVM_WITH_HEADER_MODE" \
  --override_repository="llvm++osx+macos_sdk=$SDK_REPO" \
  --@llvm//config:macos_libcxx_headers=llvm \
  --platforms=@llvm//platforms:macos_x86_64 \
  --extra_execution_platforms=@llvm//platforms:macos_x86_64 \
  //codex-rs/ansi-escape:ansi-escape-unit-tests \
  //codex-rs/keyring-store:keyring-store-unit-tests \
  //codex-rs/realtime-webrtc:realtime-webrtc-unit-tests \
  //codex-rs/sandboxing:sandboxing-unit-tests
```

The diagnostic Security and CFNetwork stubs came from SDK Gen 0.0.5.
Their SHA-256 values are
`d39d1ec11da066c0aa9a56612ff22b9f62c664e3524a7a16f859ee8aa6154097` and
`dd56930f3050ce779647aa10a2aba470ba9eed621970c3be9e060344b811fbed`
respectively.

## Voice path

`//third_party/voice:pkg_config_unix` builds on arm64 with the
diagnostic SDK. The resulting tool reports version 0.29.2 and imports
`pipe` from libSystem. The original SDK failed that same dependency
before it could build the voice host.

The four arm64 voice-host tests then reached the real native prefix
action. GLib 2.88.3 failed in `glib/gosxutils.m` because the
Foundation profile lacks `NSPathUtilities`. The required API is
`NSSearchPathForDirectoriesInDomains`, the user-domain bit, and seven
directory constants. A second diagnostic copy adds those declarations.
It uses Apple's public Objective-C API documentation and the numeric
values and underlying type from the pinned Swift Foundation
implementation. Both Objective-C and modular Objective-C++ clients
returned the expected paths on arm64 and x86_64. The same fixture also
passed against Xcode 26.5.
[Apple's directory search documentation](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/LowLevelFileMgmt/Articles/StandardDirectories.html)
· [Pinned Swift Foundation enum values](https://github.com/swiftlang/swift-foundation/blob/511394753aa873fd390674301594b4bb8460a74b/Sources/FoundationEssentials/FileManager/SwiftFileManager.swift#L170-L215)

On the next voice attempt, GLib compiled `gosxutils.m` and stopped at
`gio/gcontenttype-osx.m` on `CoreServices/CoreServices.h`. All four
voice test targets failed to build before test execution. The
`voice-host-packaged_runtime-test` fixture also requires a built
`//third_party/voice:native_runtime` exposed through
`CODEX_TEST_VOICE_RUNTIME` before its ignored native initialization
test can be exercised.

The GLib Cocoa selector also builds the following sources in the same
configuration. These are inspected requirements beyond the first
compiler stop.

| Selected source | SDK surface to qualify |
|---|---|
| GLib `gio/gcontenttype-osx.m` | CoreServices uniform type identifier functions and data exports through the umbrella |
| GLib `gio/gosxappinfo.m` | ApplicationServices and its LaunchServices APIs such as `LSCopyApplicationURLsForBundleIdentifier`, plus Foundation bundle and URL methods |
| GLib `gio/gnextstepsettingsbackend.m` | `NSUserDefaults`, autorelease pools, mutable collections, string encodings, and scalar `NSNumber` methods |
| GLib `gio/gcocoanotificationbackend.m` | Cocoa notifications, `NSImage`, and Foundation bundles |
| GStreamer `gst/gstmacos.m` | The AppKit application delegate, `NSApp`, activation policies, and event loop |

SDK Gen 0.0.5's CoreServices umbrella fails in Objective-C on both CPUs.
Its fallback CoreFoundation link macros emit `extern "C"`. After
guarding that syntax, the same include reaches a generated DriverKit
dependency on absent `kernel/kernel.h`. The released stub also lacks the
uniform type identifier data constants used by GLib.

SDK Gen merged the linkage correction in
[#15](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/15).
[#17](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/17)
fixes the generated CoreFoundation and dispatch import paths, resolves the
documented `mach_port_t` to XNU's public `mach/port.h`, and places C
availability attributes on their declarations.
[#16](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/16)
removes false linker exports for C enum cases such as
`_kLSLaunchDefaults` while preserving data symbols that DocC supplies.

### CoreServices and ApplicationServices trial

The native arm64 `//third_party/voice:native_prefix` build was rerun in
this order against separate copies of the diagnostic SDK:

| Added layer | Native build result |
|---|---|
| CoreServices UTI declarations and LaunchServices stub | GLib compiled `gcontenttype-osx.m`. `gosxappinfo.m` stopped at the missing ApplicationServices umbrella. |
| ApplicationServices umbrella, remaining LaunchServices declarations, and AppKit reexport | `gosxappinfo.m` reached missing Foundation declarations for `NSBundle`, `NSUTF8StringEncoding`, and `NSAutoreleasePool`. The notification backend also failed on `NSImage`, `NSUserNotificationCenterDelegate`, and dictionary subscripting. |
| Make-generated CoreServices and ApplicationServices recipes | The same Foundation and AppKit diagnostics reproduced on arm64 and on the x86_64 target with Rosetta. |

The [CoreServices](../frameworks/CoreServices/provenance.md) and
[ApplicationServices](../frameworks/ApplicationServices/provenance.md)
recipes stage the interfaces used in the trial. Their probes compile,
link, and run with the candidate and Xcode 26.5 on arm64 and x86_64.
The ApplicationServices probe also passes with Objective-C++ modules
against the candidate. Its Mach-O imports bind through CoreServices on
both CPUs, matching Xcode for GLib's existing AppKit and CoreFoundation
link line. The default composition continues to use its qualified
framework inputs.

To replay the native prefix from the Codex workspace, use the diagnostic
Bazel repository containing the candidate `sysroot`:

```sh
bazel --nohome_rc build --disk_cache= \
  --override_module="llvm=$LLVM_WITH_HEADER_MODE" \
  --override_repository="llvm++osx+macos_sdk=$VOICE_SDK_REPO" \
  --@llvm//config:macos_libcxx_headers=llvm \
  --platforms=@llvm//platforms:macos_arm64 \
  //third_party/voice:native_prefix
```

For the x86_64 target on Apple Silicon, select the x86_64 target and
execution platforms. GNU Make 4.4.1's configure script can still
identify its host as arm64. It then sets `__arm__` for an x86_64
compiler, includes both architecture versions of libkern's byte order
helpers, and misdetects types such as `pid_t` and `ssize_t`. A minimal
x86_64 client that defines `__arm__` before including `stdlib.h`
reproduces the same redefinitions with Xcode 26.5 and the candidate.
The normal x86_64 include passes in both. With the host override on exec
actions, the replay built GNU Make and pkg-config, compiled
`gcontenttype-osx.m`, and reached the same GLib failures as arm64:

```sh
--platforms=@llvm//platforms:macos_x86_64 \
--extra_execution_platforms=@llvm//platforms:macos_x86_64 \
--host_action_env="ac_cv_host=x86_64-apple-darwin$(uname -r)"
```

The machine-readable CoreServices DocC index has the UTI functions and
omits the six UTI data globals used here. The installed Mac confirms
LaunchServices owns those data exports. The original umbrella also
needs type-level dependency attribution for its DriverKit imports and
any remaining Kernel DocC references. Upstream still needs a
source-backed way to represent legacy data declarations, packed records,
and ApplicationServices reexports.
The local profile covers the GLib requirements. Other CoreServices
children, including the separate FSEvents work, and broader
ApplicationServices coverage remain open. Native voice runtime
packaging and tests remain blocked by the Foundation and AppKit
interfaces found in the reruns above.

### Expanded SDK Gen composition replay

The [expanded SDK](composition-gaps.md#expanded-public-framework-composition)
with the Apple OSS Security overlay passed the Codex keyring and sandboxing
tests on arm64. The native voice prefix still fails earlier, while building
pkg-config's bundled GLib. The SDK Gen libSystem stub advertises `_pipe2`,
so configure enables it. The macOS 26.5 header and runtime omit that API.
This needs an SDK-version correction in the stub, with the Foundation and
AppKit gaps above still open.

### Source-backed macOS 26.5 replay

Codex `53fe98bdc22c19b9520b0d033c2b0a1b0be62bcb` uses
`rules_foreign_cc` to configure and build GNU Make and the pinned
pkg-config 0.29.2. The pkg-config action sets `PKG_CONFIG=/bin/false`
and selects the Bazel LLVM archive tools and linker. The voice recipe
then passes the built executable to CMake and Meson, with an empty
`PKG_CONFIG_PATH` and `PKG_CONFIG_LIBDIR` restricted to the staged prefix.
The version-matched comparison SDK built pkg-config on arm64 and
x86_64. The actual binaries import `pipe` through libSystem.

GNU Make exposed a missing `environ` data import in the source-backed
preview. The pinned dyld implementation defines the object and both
macOS 26.5.2 runtime slices export it through libdyld. The candidate and
reference both linked and ran a client reading `environ` and
`_NSGetEnviron()` on both CPUs at deployment minima 11.0 and 26.5.
[Pinned Apple OSS definition](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/libdyld/libdyldGlue.cpp#L1206-L1212)
· [Versioned export preview](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/21)

The next pkg-config link needed eight out-of-line ctype functions such
as `isalpha`. Apple's Libc uses `isctype.c` to emit external versions.
InstallAPI with `-D_DONT_USE_CTYPE_INLINE_` exposes the client declarations
in the installed `_ctype.h`. Keep the 23 names confirmed by both runtime
slices. All 23 also occur in the Xcode 26.5 libsystem_c documents.
[Apple's pinned isctype.c](https://github.com/apple-oss-distributions/Libc/blob/4e34d0559e3a1b081afeb8604d9e204a1f31321d/locale/isctype.c)

The regenerated stub builds the pinned pkg-config target on arm64
and x86_64. Both binaries run and import `isspace` and `pipe` through
libSystem. The Intel target and executable were exercised with Rosetta,
using the x86_64 execution platform and configure host override above.

The arm64 voice prefix built and installed GLib with the narrow SDK. It
stopped at GStreamer 1.28.6's explicit `Cocoa` dependency in
`gst/meson.build:178`. The next local SDK stages the existing Foundation,
AppKit, Core Data, Cocoa, CoreServices and ApplicationServices recipes,
using an SDK Gen Foundation stub generated with `--sdk-version 26.5`.
The Foundation recipe restores its verified CoreFoundation reexport.
The Foundation, Cocoa, CoreServices and ApplicationServices
compile-link-run probes passed on arm64 and x86_64.

With Cocoa staged, the native arm64 build enabled GLib's Objective-C
code and failed compiling `glib/gosxutils.m` on the missing Foundation
path API. SDK Gen's generated Foundation umbrella also imports AppKit
and unrelated frameworks. The umbrella renders
`NSDocumentDirectory = 14` and `NSUserDomainMask = 4` from its fallback
enum policy. Pinned Swift Foundation supplies 9 and 1 respectively.
The existing diagnostic header supplies the verified declarations and
values to the local Foundation profile. The directory runtime fixture
passed with the 26.5 Foundation stub on both CPUs.
[Pinned Swift Foundation values](https://github.com/swiftlang/swift-foundation/blob/511394753aa873fd390674301594b4bb8460a74b/Sources/FoundationEssentials/FileManager/SwiftFileManager.swift#L170-L219)

The arm64 replay with that header got past `gosxutils.m`. The native
prefix now stops in GLib's GIO Objective-C backends. `gosxappinfo.m`
needs `NSBundle`, `NSUTF8StringEncoding` and `NSAutoreleasePool`.
`gcocoanotificationbackend.m` needs AppKit's `NSImage`,
`NSUserNotificationCenterDelegate` and the Foundation collection
subscripting methods. Qualify these interfaces from public headers or
independently sourced declarations before rerunning the native prefix.
The Cocoa header overlay and its diagnostic remain local under
`build/darwin-inventory-26.5.kUsWl8/voice-cocoa-paths-repo`.

Follow-up for Codex: evaluate a pinned native pkgconf tool, keeping the
same staged-prefix lookup. The Windows voice build already selects a
pinned pkgconf package. This would eliminate the Unix pkg-config and
bundled GLib bootstrap from consumers of that tool.

### Foundation and AppKit generation

The 26.5 generation in `build/foundation-voice-qualification` applies
three SDK Gen changes. The header regression tests failed before each
change and passed afterward for arm64 and x86_64.

- [PR #22](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/22)
  forward-declares foreign Objective-C classes used through pointers
  and keeps required imports for superclasses. It also resolves
  Objective-C types supplied by the preamble without a fictional
  `ObjectiveC/ObjectiveC.h` umbrella.
- [PR #23](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/23)
  renders the anonymous constants documented under `NSStringEncoding`
  and uses pinned Swift Foundation values for search paths and domains.
  The full generated Foundation header contains
  `NSUTF8StringEncoding = 4`, `NSDocumentDirectory = 9` and
  `NSUserDomainMask = 1`.
- [PR #24](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/24)
  keeps top-level declarations outside Objective-C interfaces. DocC
  lists `NSApplicationDelegate`, `NSApp` and the activation-policy enum
  among the topics of `NSApplication`. They are not its methods.

The selected AppKit headers and stubs generated from DocC linked and ran
the `NSImage` and `NSEvent` probes on arm64 and x86_64. The event probe
also compiles methods using `NSApplication`, `NSApp` and an
`NSApplicationDelegate` implementation. The numeric inputs for those
event and activation-policy cases were corroborated with pinned
[GNUstep NSEvent.h](https://github.com/gnustep/libs-gui/blob/af9ee9812aaef80a00645b3dcea29ab4d0eef8d8/Headers/AppKit/NSEvent.h)
and [NSRunningApplication.h](https://github.com/gnustep/libs-gui/blob/af9ee9812aaef80a00645b3dcea29ab4d0eef8d8/Headers/AppKit/NSRunningApplication.h).
The selected declaration script is `generate-appkit-probe.py` in the
trial directory. Compiling a delegate class exposed
`__objc_empty_cache`, an exported objc4 global on both targets. The
inventory fix is in
[PR #21](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/21).
Foundation and Cocoa link and module probes passed with the local
framework recipes and the updated objc4 stub.

The full regenerated Foundation and AppKit bundles fail direct imports
on both CPUs. Foundation enters AppKit and then CoreData before
defining `NSObject`-based interfaces such as `NSArray`. AppKit enters
Foundation and reaches `CloudKit/CloudKit.h`. With the selected
`NSImage` bundle in place of full AppKit, Foundation reaches the same
CloudKit failure. The precise diagnostics are in
`full-Foundation-{arm64,x86_64}.log` and
`full-AppKit-{arm64,x86_64}.log` in the trial directory.

DocC attributes CloudKit sharing methods to Foundation's
`NSItemProvider` topic. Xcode 26.5's header layout, used for comparison,
locates them in `CloudKit/NSItemProvider+CKSharingSupport.h`. The same
pattern puts AppKit's `applyFontTraits:range:` on Foundation's
`NSMutableAttributedString` topic. The full generator needs to place
these extensions in the framework that supplies them and to keep their
dependencies out of Foundation's base declarations. A single warm
crawl entry for Foundation's cookie setter returned HTTP 403.

The full-bundle header compile gate precedes the native prefix,
runtime and voice-host suite. Re-run that gate after correcting
framework ownership.

For the next voice replay, use the local Foundation headers and defer
SDK Gen's category ownership change. The local
`build/foundation-voice-qualification/voice-local-foundation` Bazel
repository adds the Foundation declarations used by GLib to the
existing header recipe. It stages the previously verified AppKit
declarations for resource images and the GStreamer event loop.
The compile-link-run fixture checks Foundation bundle lookup, UTF-8
conversion, collections, enumeration and scalar values on both CPUs.

[SDK Gen PR #25](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/25)
supplies the five AppKit event and activation values. The complete
26.5 AppKit output emits the same values as the source-backed event
fixture. The event fixture passed with the emitted values on arm64
and x86_64. The
[PR #17 follow-up](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/17)
maps `au_asid_t`, `int8_t` and `uint16_t` to the installed
`bsm/audit.h` and `stdint.h`. The regenerated Foundation header
imports both and has no `kernel/kernel.h` import.

## Standalone CLI

The configured action graph for `//codex-rs/cli:codex` has no
`VoiceNativePrefix` or `VoiceNativeRuntime` action. The CLI target reached
its own final Rust executable link. A replay of that Bazel action with
LLD's error limit disabled reported these missing framework inputs and
17 Mach-O imports.

| Framework link input | Missing imports or link requirement |
|---|---|
| CoreGraphics | `CGSessionCopyCurrentDictionary` for the terminal session check |
| LocalAuthentication | The Rust link explicitly requests the framework |
| CoreServices | `FSEventStreamCreate`, `FSEventStreamGetDeviceBeingWatched`, `FSEventStreamInvalidate`, `FSEventStreamRelease`, `FSEventStreamScheduleWithRunLoop`, `FSEventStreamStart`, `FSEventStreamStop`, `FSEventsGetCurrentEventId`, and `FSEventsPurgeEventsForDeviceUpToEventId` |
| AppKit | `NSPasteboardTypeHTML`, `NSPasteboardTypeString`, `NSPasteboardTypeTIFF`, and `NSPasteboardURLReadingFileURLsOnlyKey` |
| IOKit | `IOPMAssertionCreateWithName` and `IOPMAssertionRelease` |
| CoreFoundation | `CFPreferencesAppValueIsForced` |

All named exports exist in SDK Gen 0.0.5. On macOS 26.5.2, each
export resolves through its listed framework on arm64 and x86_64. The
session check resolves through CoreGraphics to SkyLight, and file
watching resolves through CoreServices to FSEvents. Keep the actual
reexports in mind if qualifying a production replacement.
Both IOKit power assertion functions have declarations in the matching
macOS 26.5 Apple OSS IOKitUser gitlink.
[Pinned IOKitUser header](https://github.com/apple-oss-distributions/IOKitUser/blob/23a611d9d194b63465f6df2abfdda63d71c87e97/pwr_mgt.subproj/IOPMLib.h)

The CLI-only diagnostic stages the three missing SDK Gen stubs and
supplements the existing AppKit, IOKit, and CoreFoundation stubs with
just the observed imports. It adds zero framework headers. Replaying the
arm64 Bazel link with this layer produced an executable that printed
`codex-cli 0.0.0`. The ordinary Bazel build then passed on arm64 and
x86_64 using the same SDK repository overlay. Both binaries had the
expected Mach-O architecture, loaded the six framework link inputs, and
ran `--version`. The diagnostic layer remains separate from the
qualified SDK archive.

```sh
for cpu in arm64 x86_64; do
  bazel --nohome_rc build --disk_cache= \
    --override_module="llvm=$LLVM_WITH_HEADER_MODE" \
    --override_repository="llvm++osx+macos_sdk=$CLI_SDK_REPO" \
    --@llvm//config:macos_libcxx_headers=llvm \
    --platforms="@llvm//platforms:macos_$cpu" //codex-rs/cli:codex || exit 1
  bazel-bin/codex-rs/cli/codex --version || exit 1
done
```

## SDK issues for review

| Issue | Evidence | Proposed next step |
|---|---|---|
| Codex's pinned toolchain expects SDK C++ headers | The process wrapper and AWS-LC fail as described above. The SDK intentionally delegates libc++ and libc++abi headers to the toolchain. | Use a hermetic-llvm pin with the tested LLVM header mode in Codex. Keep the mode opt-in. |
| Security is header-only in this SDK | `keyring-store-unit-tests` fails with `framework not found for -framework Security` and an undefined `SecCopyErrorMessageString`. A C client of `Authorization.h` fails on both CPUs. It links against Xcode 26.5 and against the existing SDK Gen 0.0.5 `Security.tbd` used as a diagnostic input. | Qualify the SDK Gen stub against the Rust keyring client before adding it to composition. For clients that compile Security headers, start with the Apple OSS public install rules. |
| CFNetwork is absent | The arm64 `sandboxing-unit-tests` link requests both CFNetwork and Security. Its Security imports also include certificate and trust-settings APIs. SDK Gen 0.0.5 has a CFNetwork stub and contains all four named Security exports. | Qualify both stubs against the sandboxing target. Stage only the linker files while this consumer gets its declarations from Rust. |
| The inherited 27.0 libSystem advertises `pipe2` in a 26.5 archive | Codex's bundled pkg-config configures its internal GLib with `pipe2` enabled, then `glib-unix.c` fails to compile. The composed stub resolves a strong `_pipe2` import on both CPUs. Xcode 26.5 declines the same link. The trial includes that name under both `libsystem_kernel` and `libsystem_sim_kernel`. Runtime lookup on 26.5.2 finds neither `pipe2` nor the related `dup3`, which is also advertised by the stub. [macOS 27 compatibility report](https://github.com/python/cpython/issues/153711) | Select libSystem exports by SDK version and target in the composition. The local diagnostic removes the two exact `_pipe2` entries and reproduces the reference link failure on both CPUs. Keep 27.0 support in the 27.0 generator output. |
| Foundation path-search declarations | GLib's `gosxutils.m` cannot compile the path lookup. The independently sourced header passes the two-architecture path probe. SDK Gen 0.0.5's generated Foundation header repeats the type name for every case in `NSSearchPathDirectory`. | Add the tested header profile after review. [SDK Gen PR #14](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/14) fixes case names. Qualify numeric values independently. |
| CoreServices header, typed data exports, and dependencies | The GLib profile passes its probes on both CPUs. SDK Gen's generated umbrella and other subframeworks still have the coverage gaps above. | Resolve DocC types to their actual C headers and qualify a broader CoreServices reexport tree. |
| ApplicationServices umbrella and reexports | The local umbrella and AppKit reexport get GLib to Foundation compilation. GLib stops before its link step. | Use the two-architecture LaunchServices ABI and link probe when extending the umbrella. |

[SDK Gen PR #4](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/4)
already tracks preserving each SDK's Darwin library documents and target
groups. A 26.5 composition still needs a matching version of those export
facts. The SDK Gen 27.0 output remains a different input.

## Codex SDK selection

Codex's `osx.frameworks` names 41 frameworks. The trial contains link
stubs for 12 and the Security authorization header. The other 28
requested framework directories are absent:

```text
ApplicationServices AVFAudio AVFoundation AVRouting CFNetwork ColorSync
CoreGraphics CoreImage CoreMedia CoreServices CoreText CoreVideo DiskArbitration
FontServices ImageIO IOSurface Kernel LocalAuthentication Metal MetalKit
OpenGL OSLog PrintCore QuartzCore ScreenCaptureKit Symbols
UniformTypeIdentifiers VideoToolbox
```

SDK Gen 0.0.5 contains framework directories for 23 of the 28 names.
ApplicationServices, FontServices, Kernel, OpenGL, and PrintCore have no
directory in that release. This is a comparison of the workspace's SDK
selection. Use action and linker diagnostics to decide which names a
specific target needs.

The requested `libproc.tbd` exists as an alias to libSystem. Xcode
26.5 also aliases it to libSystem. The standalone `libsandbox.tbd` is
absent and SDK Gen 0.0.5 has the alias and versioned stub. The trial's
libSystem already exposes the `sandbox_check` and
`SANDBOX_CHECK_NO_REPORT` names called by Codex's Seatbelt tests.

## Local evidence

The diagnostic inputs and logs are in the worktree's
`build/codex-sdk-check.RqcR2E` directory. Its `llvm-upstream-libcxx`
directory supplies `LLVM_WITH_HEADER_MODE`. Use
`sdk-repo-voice-diagnostic` for the focused targets and
`sdk-repo-cli-diagnostic` for the CLI. The full failed-link inventory
is in `arm64-cli-link-replay.log`, and the successful CLI runs are in
the two `*-cli-composed-build.log` and `*-cli-composed-smoke.log` pairs.

## Arm64 voice runtime packaging

At Codex `53fe98bdc22c19b9520b0d033c2b0a1b0be62bcb`, the local
Foundation and AppKit voice profiles let the native GLib and GStreamer
prefix build. Using the runtime's `Versions/C` Foundation and AppKit
install names fixed packaging. Both `//third_party/voice:native_prefix`
and `//third_party/voice:native_runtime` passed with the same 26.5 scratch
SDK. The generated `runtime.json` records the versioned identities.
[SDK Gen PR #26](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/26)

The exact voice-host test invocation then failed at the Rust executable
link on `-framework AudioToolbox` and `-framework CoreAudio`. The trial
omitted those bundles. The existing local profiles cover their older C
tests, with additional linker coverage needed for the voice host. The
first unresolved names include `AudioUnitRender`,
`AudioHardwareCreateProcessTap`, and `AudioObjectGetPropertyData`.

The SDK repository override is
`build/foundation-voice-qualification/voice-versioned-frameworks`.
The same directory contains `versioned-voice-arm64.log` and
`versioned-voice-tests-arm64.log`. The scratch Foundation/AppKit voice
profiles still need to be represented in the framework recipes before
this exact build can be replayed from a fresh checkout.

### Audio framework replay

The version-matched 26.5 starting preview requested only CoreGraphics,
Network, and Security. Later layers added the frameworks needed for the
native prefix. The older full SDK Gen artifact already has the audio
exports, so reproduce with the version-matched generator before adding
local declarations or stub entries.

Run SDK Gen on macOS platform only with `--sdk-version 26.5` and the same
version-matched Darwin metadata. The isolated generator at
`7a7aaf29f0c75d809c83e170645ed92d1686f424` ran with
`--frameworks AudioToolbox,CoreAudio,AudioUnit,CoreAudioTypes` and produced
all four bundles through its ordinary generation path. The same
scratch directory contains the command output in `audio-pristine.log`.

The link-only client `voice-audio-imports.c` references the 18 audio names
reported by the first Rust link. It fails against the earlier preview
and links against both Xcode 26.5 and the four freshly generated bundles
in `voice-sdk-gen-audio`. The Mach-O undefined symbols match in name and
bind-through framework. Both probe libraries load on macOS 26.5.2. SDK Gen
still records flat audio install names where Xcode uses `Versions/A`.
`AudioToolbox` and `CoreAudio` are independent link inputs. These probes
measure linker coverage for the Rust consumer. C and Objective-C header
coverage has separate probes.

Codex's arm64 native prefix and runtime package build with
`voice-sdk-gen-audio`. The unmodified voice host links and passes all four
Bazel test targets on macOS 26.5.2. The unit (56 cases), installed client
(2), lifecycle (3), and relocated native runtime (1) cases ran. The
packaged test uses `--test_arg=--include-ignored` and
`CODEX_TEST_VOICE_RUNTIME` pointing to the native runtime from the same
build. The unit suite's ignored subprocess fixture is exercised by its
watchdog test.

The first installed-client run passed its two cases and Bazel's
`generate-xml.sh` then segfaulted. The local replay uses
`--test_env=LC_ALL=C`, consistent with the Bazel integration workspace.
The successful logs are `sdk-gen-audio-voice-tests-arm64-locale-c.log`
and `sdk-gen-audio-packaged-runtime-arm64.log`.

For the full composition, generate macOS 26.5 with SDK Gen's
`--all-frameworks`, then pass `--all-frameworks` to our composer with the
qualified recipe overlays. A targeted preview only contains the
frameworks selected in its SDK Gen invocation.
