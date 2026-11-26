# Foundation and Cocoa qualification

The consumer archive must preserve the qualified macOS 26.5 C, Objective-C
runtime, networking, and audio layers. Add Foundation and Cocoa and exercise
their headers, linkage, and runtime behavior on arm64 and x86_64 before running
the existing Stage 1 Clang and consumer gates on the exact archive.

## Baseline

- The networking archive with SHA-256
  `08a0c6b5b9410d695b78509a3297c5f1ae87ee7f39df2117f7ffa27af9fafc87`
  passed both architectures in all three integration gates. The C, DNS-SD,
  CoreFoundation, SystemConfiguration, resolver, and audio checks also passed.
- SDK Gen 0.0.5 was built from `41217f0f527f1d249e8cf10c7d411a95ff7be4d2`.
  The resolver's 155 exports match the source-derived stub on both targets.
  The released libSystem still needs the documented x86_64-only compiler-rt
  correction. Keep the qualified networking and audio recipes for the trial.
- The new Foundation umbrella expands into Contacts and fails on duplicate
  enum cases. Cocoa PR #11 supplies a working umbrella and reexports with
  isolated fixtures. Against the released child frameworks, Cocoa reaches
  the same Contacts error on both targets.

## SDK Gen follow-up

SDK Gen 0.0.5 includes PRs #3 and #5–10. The resolver regression is
resolved in the released artifact. Keep the source-derived resolver recipe
until the release also passes the existing integration link cases.

| Change | Evidence | Status |
|---|---|---|
| Generate Cocoa from Foundation, AppKit, and Core Data | Apple documents the imports. The loaded macOS library reexports AppKit and Core Data. SDK Gen uses flat child install names. | [PR #11](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/11) and both architectures tested with isolated fixtures. |
| Preserve the enumerator name in Objective-C USRs | The public DocC page for `CNAuthorizationStatusAuthorized` identifies `c:@E@CNAuthorizationStatus@CNAuthorizationStatusAuthorized`. The regression failed against the old generator and passes with the fix. Codex's voice build also needs the affected Foundation directory enum. | [PR #14](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/14), commit `8c5c0ad`. A real Contacts regeneration moved both probes past the repeated enum names. |
| Keep enum constants out of TBD exports and qualify their values | `utils/usr_parser.py` maps an enum-case USR to a Mach-O export. `generators/objc_header.py` guesses unknown values from topic order or a bit index. | Open. Filter compile-time constants from linker output. Use independently established values and report unresolved cases. |
| Retain Objective-C-only class and protocol member references | The class renderer calls `_find_children` on the parsed parent. The crawler discovers Objective-C variant pages, but the parser reads the default topic list. The live NSString page lists `stringWithUTF8String:` exclusively in its Objective-C topics. | Local `a1df0d2` merges Objective-C topics without discarding the default child list. The regression and a cached real NSString parse pass. |
| Add the Foundation to CoreFoundation reexport | The installed Foundation dylib reexports CoreFoundation, which owns the constant-string class reference. A Foundation-only application compiled and failed at link until the edge was restored. | Qualified locally with the staged CoreFoundation alias. SDK Gen's flat CoreFoundation stub needs the matching flat reexport. |
| Retain AppKit's Foundation reexport in the profile | The loaded AppKit image reexports Foundation. Cocoa clients may create Foundation objects and string literals through that dependency. | Local AppKit InstallAPI recipe. |
| Resolve the generated framework dependency chain | After the Contacts regeneration, both architectures report undeclared protocols and invalid type declarations reached through Foundation. The full diagnostic also reaches a missing `kernel/kernel.h` import. | Open. Map DocC modules to real headers, forward-declare object pointer types where possible, order class definitions by superclass, and inspect generic and by-value layouts separately. |
| Guard CoreFoundation C linkage macros in generated umbrellas | The released CoreServices umbrella defines `CF_EXTERN_C_BEGIN` before it imports CoreFoundation. The macro emits C++ syntax in Objective-C. | [PR #15](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/15) fixes the four language modes. CoreServices still reaches a generated missing kernel include. |
| Include forwarding headers in module maps | A direct import of the generated `Foundation/NSString.h` fails under Clang modules with a missing submodule. Marking a forwarding header textual lets Clang load the umbrella through it. | Local recipe now emits textual entries for its wrappers. Verify the same behavior before changing SDK Gen's module generator. |
| Land the macOS preview on `main` | The stacked preview PR merged into the manual release branch after the latter was merged into `main`. The default branch lists Tests and Release. | [PR #13](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/13) holds the preview diff to carry onto `main`. |
| Preserve per-architecture Darwin stub exports | The 0.0.5 arm64 stub still exposes three complex division helpers absent from arm64 libSystem. LLVM supplies these from builtins. | [PR #4](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/4) remains open. Qualify each new release against the runtime and the LLVM OpenMP case before dropping the local correction. |
| Qualify generated CF, reachability, and audio layers | The released generated frameworks still fail the existing consumer-facing C profiles. Source-backed CoreFoundation and configd and the local audio ABI profile pass the same fixtures. | Open. Keep the existing recipes and use their fixtures when assessing future SDK Gen output. |

## C SDK follow-up

- Keep the Foundation and Cocoa fixtures beside their framework packages.
  Both fixtures compile, link, and run against Xcode 26.5 on both CPUs.
- Record the input digest and provenance of each new framework layer in
  the trial. Compare SDK coverage and ABI against the official SDK, which
  serves as a reference for the probes.
- Stage the optional Foundation, AppKit, Core Data, and Cocoa profiles with
  package-specific provenance. The released generated frameworks still lack
  broad independent coverage. Keep the scoped profiles explicit until SDK
  Gen can generate and qualify the broader declarations.
- Use the consumer recipe's Foundation linker exports with the restored
  CoreFoundation reexport. Stage the versioned CoreFoundation alias only
  when needed by this profile. Generate AppKit and Core Data class exports
  from the staged declarations with InstallAPI. Use the pinned SDK Gen
  Cocoa assembler for the umbrella and its direct reexports.
- Exercise the same declarations through direct framework headers and
  Clang's module search path. The test builds both Objective-C and modular
  Objective-C++ and runs on both architectures.
- Re-run the networking and audio probes and the three integration gates
  after assembling the new layers. Update the qualified consumer profile
  only after the exact archive passes.
- Keep the [registry consumer tests](../e2e/README.md#bazel-central-registry-consumers)
  as an additional gate for SystemConfiguration and CoreFoundation.
  The default curl TLS configuration needs a linkable Security framework.
  The trial supplies Security's Authorization header for configd, so the
  curl test selects the registry's Mbed TLS configuration. A GLFW check
  can cover Cocoa once AppKit windowing and an OpenGL layer are available.

## Trial archive

The archive SHA-256 is
`4b8bec003afa00e4612d512423790420fa231067f03dc44ec542c95ce5502cbd`.
Two independent staging and composition runs produced byte-identical
archives. Package-level provenance records which Apple OSS, public
documentation, and runtime linkage evidence each recipe uses. Xcode 26.5
provided comparison results for the fixtures and header paths.

| Framework | Headers in the trial / Xcode 26.5 | Tested surface |
|---|---:|---|
| Foundation | 12 / 173 | Strings, collections, data, errors, URLs, values, numbers, dates, and the range ABI |
| AppKit | 6 / 297 | sRGB colors and inheritance for NSApplication, NSView, NSResponder, and NSWindow |
| Core Data | 3 / 58 | Entity descriptions and an in-memory managed-object model |
| Cocoa | 1 / 1 | Umbrella imports for Foundation, AppKit, and Core Data and Cocoa's reexports |

These counts describe header paths. The local declarations cover the
exercised interfaces within those headers.

The [Codex consumer check](codex-consumer-check.md) tracks the later CLI
and voice experiments against diagnostic copies of this archive.

The unpacked archive passed 30 framework and four networking checks across
arm64 and x86_64. The Foundation and Cocoa fixtures pass in Objective-C and
modular Objective-C++. Both Stage 1 Clang builds passed with
`--config=remote`.

The local consumer suites used the same archive on both architectures.
Each rules_rs run passed 39 tests. Each hermetic-llvm run passed 38 tests
with 45 skipped. Both Bazel entry points resolved the archive at
`build/sdk/MacOSX.sdk.tar.zst`, and the extracted composition receipts
match the trial tree.

The registry c-ares and curl tests also passed locally on arm64 and
x86_64 using the same archive. The linked curl program imports
`SCDynamicStoreCopyProxies` from SystemConfiguration and `CFRelease`
from CoreFoundation.

The C installation passed all 384 compile checks and the arm64 floating
point runtime check. The candidate retains all 895 manifest entries
outside Foundation from the previous archive. It includes no libc++
headers, static libraries, or dylib binaries. The platform C++ linkage
stubs remain available to toolchains that target the system runtime.

- [Arm64 Stage 1 Clang](https://app.buildbuddy.io/invocation/d997aec6-3d68-4bf4-a705-6555cd4d5650)
- [x86_64 Stage 1 Clang](https://app.buildbuddy.io/invocation/1e574812-8f18-4f98-b37a-baa82552273d)
