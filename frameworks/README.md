# Framework recipes for the macOS consumer SDK

These recipes build the framework layers for the macOS 26.5 composition.
Each recipe lists its source and stages one `.framework` directory. The
Security layer supplies Apple's public umbrella and its include closure,
including the authorization header used by SystemConfiguration. The
expanded composition retains SDK Gen's Security stub. The original consumer
composition takes Foundation directly from SDK Gen. The Objective-C trial
uses the profiles below.

From the repository root, set `C_INSTALL` to the generated C tree and
`LLVM` to the pinned LLVM projection containing `bin/clang` and
`bin/clang-installapi`.

```sh
make -C frameworks prepare
make -C frameworks install CLANG="$LLVM/bin/clang" C_INSTALL="$C_INSTALL" OUT="$PWD/build/frameworks"
```

`prepare` fetches the pinned CF, IOAudioFamily, OpenAL, Security and configd
commits into `build/framework-sources`. Set `SOURCE_ROOT` to an absolute
directory containing those Git repositories to use existing objects.
`install` reads the pinned objects offline and writes into a new output
directory. To stage a subset, pass `FRAMEWORKS="CoreFoundation OpenAL"`,
for example. SystemConfiguration also stages CoreFoundation and Security.

The recipes use Make, shell, Git, and standard tools. They take no
official SDK path. Each framework's `provenance.md` identifies its inputs,
the scope of the repair, and the available source evidence. The
[composition instructions](../tools/sdk_composition/README.md#expanded-framework-trial)
use the resulting directories as prepared bundles or overlays.

```sh
make -C frameworks test CLANG="$LLVM/bin/clang" SDK="$NEW_SDK"
```

Each framework in the default set has a `test.c` beside its recipe. The probes check
signatures, record layouts, or linkage on arm64. CoreAudioTypes,
IOKit and Security run compile checks. SystemConfiguration compiles its
reachability header directly and links a separate client of the umbrella.
Use `test-OpenAL`, for example, to run a single framework's probe.

On Apple Silicon, add `RUN=1` to execute
the linked probes. CoreFoundation, AudioToolbox and SystemConfiguration
call their tested APIs. The other linked probes exercise dynamic loading
and symbol binding.

## Objective-C framework trial

Stage Cocoa and its dependency profiles by adding `Cocoa` to `FRAMEWORKS`.
Pass `OBJC4_INSTALL` as the pinned Objective-C runtime header installation,
`FOUNDATION_TBD` as the qualified SDK Gen 0.0.4 Foundation stub, and
`SDK_GEN_SOURCE` as a Git checkout containing the Cocoa recipe from PR #11.
The package notes describe the selected public declarations and provenance.

The Foundation probe exercises strings, an `NSRange` return value,
collections, data, errors, URLs, and scalar values. The Cocoa probe links
through the umbrella to exercise an AppKit color, the responder class
hierarchy, and an in-memory Core Data model.

```sh
make -C frameworks -k test-objc CLANG="$LLVM/bin/clang" SDK="$NEW_SDK" RUN=1
```

Both probes compile, link, and run as Objective-C and as Objective-C++ with
Clang modules on arm64. `test-Foundation` and `test-Cocoa` also run individually.

## LaunchServices trial

Select `FRAMEWORKS="AppKit ApplicationServices"` with the Objective-C inputs
above. The recipe stages CoreServices and its LaunchServices child and
includes the ApplicationServices reexport in AppKit. The profiles cover
the LaunchServices APIs required by GLib. See the package provenance files
for the remaining framework coverage.

```sh
make -C frameworks test-CoreServices test-ApplicationServices \
  CLANG="$LLVM/bin/clang" SDK="$NEW_SDK" RUN=1
```
