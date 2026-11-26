# Compose a macOS consumer SDK

Run the [release build](../../release/README.md) to generate and compose a fresh SDK.
The commands below document individual inputs and earlier profiles.
Set `PYTHONPATH` to include the pinned C SDK checkout.

The composer combines a source-locked macOS 26.5 C installation, pinned
`objc4` headers, and named Apple SDK Gen assets. It copies the SDK Gen
libSystem TBD unchanged and records the source SDK name separately from the
generated SDK settings. Pass `--include-cxx` to include the fork’s LLVM
libc++ and libc++abi headers and license files. Set up the linker inputs
from the same SDK Gen tree. The C++ programs link against the macOS
system dylibs.

The composer restores the macOS compatibility names from Apple's Libsystem
install rule as links to the unchanged SDK Gen umbrella. This lets
`-ldl`, `-lm` and `-lpthread` bind through libSystem.
[Apple Libsystem install rule](https://github.com/apple-oss-distributions/Libsystem/blob/c23b51183e46e613375dc7639fb4bf11fbf59ba8/xcodescripts/create_dylib_symlinks.sh#L14-L31)

Use Python 3.11+, the [verified LLVM tools](https://github.com/hermeticbuild/apple-oss-c-sdk/blob/main/tools/toolchain/README.md), and the
[C and Objective-C installations](https://github.com/hermeticbuild/apple-oss-c-sdk/blob/main/locks/README.md). Before staging,
the composer checks their source locks and the SDK Gen input's
`CanonicalName` and `Version` against the macOS 26.5 profile. When using a
separate framework SDK Gen tree, both SDK Gen trees must pass the same
version check. Select a 26.5 preview generated with a matching Darwin
inventory. The version check reads the input settings and the composition
manifest records the selected file digests.

Set `SDK_GEN` to the extracted `MacOSX.sdk` and `NEW_SDK` to a new output
directory named `MacOSX.sdk`. The command below composes a smoke SDK.
For the three consumer gates, build the layers with the
[framework recipes](../../frameworks/README.md) and include the iconv/charset
and resolver stubs.

```bash
stubs=()
for name in libc++ libc++.1 libc++abi libobjc libobjc.A libz; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$SDK_GEN/usr/lib/$name.tbd")
done
python3 -m tools.sdk_composition.compose_sdk \
  --c-install "$C_INSTALL" --objc4-install "$OBJC4_INSTALL" \
  --sdk-gen "$SDK_GEN" --llvm "$LLVM" --framework Foundation \
  "${stubs[@]}" --out "$NEW_SDK"
```

Use `--framework NAME` to take a framework from SDK Gen. Use
`--prepared-framework NAME DIRECTORY` to take a specific prepared framework.
The composer rejects a framework or stub that shadows an SDK Gen libSystem
provider.

## Bundle the LLVM C++ headers

Generate the macOS 26.5 SDK Gen input with its `--include-cxx` flag.
It uses LLVM 21.1.6 and the upstream Apple libc++ CMake preset. Then pass
`--include-cxx` to the composer. It selects `usr/include/c++/v1` and the
two LLVM license files, and records them under `sdk-gen-cxx` in the manifest.
Use `--@llvm//config:macos_libcxx_headers=sdk` in the consumer workspace
to exercise this layer. The historical consumer archive was qualified
with headers supplied by hermetic-llvm.

## Expanded framework trial

Use `--all-frameworks` to import every SDK Gen framework under
`System/Library/Frameworks`. Set `--framework-sdk-gen` when the framework
archive and the qualified libSystem archive come from separate builds of
the same SDK version.
Use `--prepared-framework` for an entire bundle and
`--framework-overlay NAME DIRECTORY` for recipe files that add to or
replace paths in a generated bundle. All three origins appear in
`composition.json`. If a generated filename differs only in capitalization,
the overlay supplies the spelling from the source recipe.

When the framework input supplies `usr/include/simd`, the composer imports
its generated `simd.h` and module map. These provide the SIMD types used by
the Model I/O framework. Their receipts use the `sdk-gen-simd` layer.

Set `SDK_GEN_FRAMEWORKS` to the 26.5 framework input and use the matching
C, Objective-C, libSystem, and standalone stub inputs. Stage
the default recipes, Cocoa, and ApplicationServices. Pass the generated
CoreServices stub to its recipe to preserve its linker exports.

```bash
make -C frameworks prepare
make -C frameworks install CLANG="$LLVM/bin/clang" C_INSTALL="$C_INSTALL" \
  OBJC4_INSTALL="$OBJC4_INSTALL" FOUNDATION_TBD="$FOUNDATION_TBD" \
  COCOA_FRAMEWORK="$SDK_GEN/System/Library/Frameworks/Cocoa.framework" OUT="$FRAMEWORKS" \
  CORE_SERVICES_TBD="$SDK_GEN_FRAMEWORKS/System/Library/Frameworks/CoreServices.framework/CoreServices.tbd" \
  FRAMEWORKS="CoreFoundation AudioToolbox AudioUnit CoreAudio CoreAudioTypes CoreMIDI IOKit OpenAL Security SystemConfiguration Cocoa CoreServices ApplicationServices"

frameworks=()
for bundle in "$FRAMEWORKS"/*.framework; do
  name=$(basename "$bundle" .framework)
  case "$name" in
    CoreServices|Security) frameworks+=(--framework-overlay "$name" "$bundle");;
    *) frameworks+=(--prepared-framework "$name" "$bundle");;
  esac
done

python3 -m tools.sdk_composition.compose_sdk \
  --c-install "$C_INSTALL" --objc4-install "$OBJC4_INSTALL" \
  --sdk-gen "$SDK_GEN" --framework-sdk-gen "$SDK_GEN_FRAMEWORKS" \
  --all-frameworks --llvm "$LLVM" "${frameworks[@]}" "${stubs[@]}" --out "$NEW_SDK"
```

Run the [composed SDK probes](../../docs/composed-sdk-tests.md) on the expanded tree.
The digest check below applies to the original qualified asset selection.

## Reproduce the previous consumer archive

The SDK used by Stage 1 and both consumer suites requires these prepared
inputs for SDK Gen 0.0.4:

- `SDK_GEN`, the macOS SDK Gen 27.0 tree with the qualified `libSystem.B.tbd`.
  The original archive `stub-sdks-27.0.tar.zst` has SHA-256
  `e3ba6081bfcd23973dd80fe76b3c28ce8d3a98d9eb9cbc800225a649c5c07184`.
  Its compiler-rt document exposes `___divsc3`, `___divdc3`, and `___divxc3`
  on x86_64. It supplies Foundation and the six SDK Gen stubs listed above.
- `FRAMEWORKS`, the directory containing the framework layers from the
  [framework recipes](../../frameworks/README.md). The CoreFoundation and
  SystemConfiguration stubs come from their staged headers.
- `STUBS`, the generated iconv and charset layer described below.
- `RESOLVER`, the resolver layer built using the same source root as the
  C installation and Apple's [libresolv InstallAPI settings](../../stubs/libresolv/README.md).
  Pass `SOURCE_ROOT` to the resolver Make invocation when the C sources are
  outside `build/sources/macosx26.5`.

Supply these prepared inputs explicitly. The
[consumer profile](consumer-26.5.json) pins their selected files and symlink
targets from the passing archive. `--verify-consumer-inputs` checks every
selected framework and both stub groups before publishing. This flag replays
that exact SDK Gen 27.0 selection. C and Objective-C
headers are checked through their own source locks and manifests. The
[qualification evidence](../../docs/composition-gaps.md)
records the source revisions and corrections behind the prepared assets.
Use the retained qualified recipe outputs for that exact asset check.

```bash
RESOLVER="$PWD/build/resolver"
make -C stubs/libresolv C_SDK="$C_SDK" CLANG="$LLVM/bin/clang" C_INSTALL="$C_INSTALL" OUT="$RESOLVER"

frameworks=()
for name in CoreFoundation AudioToolbox AudioUnit CoreAudio CoreAudioTypes CoreMIDI IOKit OpenAL Security SystemConfiguration; do
  frameworks+=(--prepared-framework "$name" "$FRAMEWORKS/$name.framework")
done

stubs=()
for name in libc++ libc++.1 libc++abi libobjc libobjc.A libz; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$SDK_GEN/usr/lib/$name.tbd")
done
for name in libiconv libiconv.2 libcharset libcharset.1; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$STUBS/usr/lib/$name.tbd")
done
for name in libresolv libresolv.9; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$RESOLVER/usr/lib/$name.tbd")
done

python3 -m tools.sdk_composition.compose_sdk \
  --c-install "$C_INSTALL" --objc4-install "$OBJC4_INSTALL" \
  --sdk-gen "$SDK_GEN" --llvm "$LLVM" --framework Foundation \
  --verify-consumer-inputs "${frameworks[@]}" "${stubs[@]}" --out "$NEW_SDK"
```

For [Bazel validation](../../e2e/README.md), use `NEW_SDK="$PWD/build/sdk/MacOSX.sdk"`
and pack the tree as described below.

## Foundation and Cocoa trial

Use the verified C and Objective-C runtime installations and the matching
26.5 SDK Gen libSystem and external stubs. Set `FOUNDATION_TBD` to the
Foundation stub generated for macOS 26.5.

```bash
FRAMEWORKS="$PWD/build/frameworks-objc"
c_frameworks=(CoreFoundation AudioToolbox AudioUnit CoreAudio CoreAudioTypes CoreMIDI IOKit OpenAL Security SystemConfiguration)
make -C frameworks install CLANG="$LLVM/bin/clang" C_INSTALL="$C_INSTALL" \
  OBJC4_INSTALL="$OBJC4_INSTALL" COCOA_FRAMEWORK="$SDK_GEN/System/Library/Frameworks/Cocoa.framework" \
  FOUNDATION_TBD="$FOUNDATION_TBD" \
  FRAMEWORKS="${c_frameworks[*]} Cocoa" OUT="$FRAMEWORKS"

frameworks=()
for name in "${c_frameworks[@]}" Foundation QuartzCore AppKit CoreData Cocoa; do
  frameworks+=(--prepared-framework "$name" "$FRAMEWORKS/$name.framework")
done
python3 -m tools.sdk_composition.compose_sdk \
  --c-install "$C_INSTALL" --objc4-install "$OBJC4_INSTALL" \
  --sdk-gen "$SDK_GEN" --llvm "$LLVM" \
  "${frameworks[@]}" "${stubs[@]}" --out "$NEW_SDK"
```

Use the Cocoa bundle from the same generator run. The
[framework recipes](../../frameworks/README.md#objective-c-framework-trial)
declare the exact scope and provenance of the local headers. Use `test-objc`
to exercise the Foundation and Cocoa profiles against the composed tree.
The [qualification record](../../docs/objc-framework-qualification.md)
tracks their coverage and the upstream changes.

For the OpenCV backends, also stage `CoreGraphics AVFoundation`.
The Cocoa recipe stages QuartzCore through AppKit, and the AVFoundation
recipe stages CoreMedia and CoreVideo. Set
`COREGRAPHICS_FRAMEWORK` to the newly generated CoreGraphics bundle and
pass the staged bundles to the composer as prepared frameworks.

Run the backend reproducer with the SDK's bundled libc++ headers.

```sh
./repro.sh "$ARCHIVE" --@llvm//config:macos_libcxx_headers=sdk
```

## Packing release archives

Run the packer on the composed SDK. Each command prints
the SHA-256 of the compressed archive. The output directory must already exist
outside the source tree. The archive root name stays the same across builds in
different source directories.

```sh
python3 -m tools.pack_archive --source "$NEW_SDK" \
  --root-name MacOSX.sdk --output "$DIST/MacOSX.sdk.tar.zst"
```

The packer writes sorted POSIX pax tar entries with epoch timestamps and
numeric owner and group zero. It keeps file bytes, empty directories and
symlink target strings. Regular files use mode 0644 or 0755 according to
their executable bits, and hard-linked files each carry their own bytes.
Extended attributes and AppleDouble sidecars are omitted. Compression uses
the local `zstd --single-thread -6`. Use the same zstd version for both builds
when comparing release hashes.

## libiconv and libcharset

Generate the two separate libraries before composing the SDK. The producer
reads the pinned Git objects for Apple's libiconv-115.120.2, the standalone
C header installation, and the pinned macOS arm64 LLVM projection. macOS
`plutil` reads the Xcode project. The compiler uses a temporary sysroot
containing only C headers verified against the installation manifest.

```sh
python3 -m tools.sdk_composition.iconv_stubs \
  --source "$ICONV_SOURCE" --c-install "$C_INSTALL" --llvm "$LLVM" --out "$STUBS"
```

Both dylibs use the Release target's public and private header phases, product
names and versions. For libiconv the TAPI configuration supplies `-DIN_TAPI`,
the Citrus include path and the reexport of the freshly generated libcharset.
The install script specifies the two unversioned symlinks. The generated
`manifest.json` records the source revision, tool and C manifest digests,
registered headers and output digests.
[Project](https://github.com/apple-oss-distributions/libiconv/blob/7fb0198429570d3b6aa562d228a6ea5936d15c05/libiconv.xcodeproj/project.pbxproj)
· [TAPI configuration](https://github.com/apple-oss-distributions/libiconv/blob/7fb0198429570d3b6aa562d228a6ea5936d15c05/xcodeconfig/libiconv.xcconfig)
· [Install aliases](https://github.com/apple-oss-distributions/libiconv/blob/7fb0198429570d3b6aa562d228a6ea5936d15c05/xcodescripts/dest_cleanup.sh)

Append these four arguments to `compose_sdk`.

```sh
--external-stub "usr/lib/libiconv.2.tbd=$STUBS/usr/lib/libiconv.2.tbd" \
--external-stub "usr/lib/libiconv.tbd=$STUBS/usr/lib/libiconv.tbd" \
--external-stub "usr/lib/libcharset.1.tbd=$STUBS/usr/lib/libcharset.1.tbd" \
--external-stub "usr/lib/libcharset.tbd=$STUBS/usr/lib/libcharset.tbd"
```

For qualification, export `ICONV_SOURCE`, `C_INSTALL` and `LLVM` and run
`python3 -m unittest -v tools.sdk_composition.test_iconv_stubs`. The tests
check reproducibility, link an arm64 client against `-liconv`, and inspect the
two-level bindings for `iconv_open` and `locale_charset`.

Setting `ICONV_REFERENCE_SDK` additionally compares the products with the macOS
26.5 SDK. All 95 direct iconv exports and both charset exports match, including
the reexport edge and dylib versions. The producer targets macOS arm64 with
a deployment floor of 11.0. The comparison uses the reference arm64e target.
Upstream LLVM emits `not_app_extension_safe` for
these project settings. App-extension compatibility remains unqualified.
