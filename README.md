# apple-sdk-gen

Generate an arm64 macOS SDK for C, C++, Objective-C and Objective-C++.
Framework declarations come from Apple’s public documentation. Clang
module maps and linker stubs make the generated interfaces usable by
cross-compilers.

## Generate macOS 26.5

With Python 3.12 or newer, CMake, Ninja and Clang on `PATH`:

```sh
python3 -m pip install -e tools/
python3 -m tools.apple_sdk_gen --sdk-version 26.5 \
  --frameworks Cocoa,CoreFoundation,CoreGraphics,Network,Security \
  --include-cxx --cache-dir cache --output output
```

The SDK is at
`output/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk`.
The cache stores DocC responses and the LLVM source archives. Reuse it
when regenerating a framework. Selecting Cocoa requests Foundation,
AppKit and Core Data and builds an umbrella for the three.

| Flag | Purpose |
|---|---|
| `--sdk-version` | Required version of the generated SDK |
| `--darwin-library-metadata` | Override the bundled 26.5 inventory with a matching version |
| `--frameworks` | Generate a comma-separated set of frameworks |
| `--all-frameworks` | Generate discovered macOS frameworks with a C or Objective-C DocC view |
| `--exclude-frameworks` | Exclude selected frameworks, including Cocoa |
| `--include-libc` | Install the generator's optional Apple OSS C header supplement |
| `--include-cxx` | Install the macOS 26.5 LLVM C++ and ABI headers |
| `--output`, `--cache-dir` | Choose the SDK output and download cache directories |
| `--concurrency`, `--rate-limit` | Set the DocC request limits |
| `--xcode-version`, `--xcode-build` | Set the version recorded in the Xcode-style metadata |
| `-v`, `-vv` | Enable info or debug logging |

The C++ layer uses LLVM 21.1.6, the libc++ version reported by Xcode
26.5. The installer checks release archive digests and runs LLVM's
Apple CMake preset and header install targets. It includes both
LLVM license files. Consumers link to the macOS system dylibs.
[LLVM release](https://github.com/llvm/llvm-project/releases/tag/llvmorg-21.1.6)

Selecting Model I/O or `--include-libc` generates `<simd/simd.h>` and a
Clang module map. This header provides the vector, matrix and quaternion
types used by Model I/O. The generator uses C-family declarations from
the public [SIMD documentation](https://developer.apple.com/documentation/simd).

## Darwin linker stubs

The generator uses the checked-in macOS 26.5 export inventory for
`libSystem.B`, `libobjc.A`, `libc++.1` and `libc++abi`. Metadata for
another SDK must declare that version. The writer keeps the arm64
exports, reexports and owning install names.
[26.5 provenance](tools/apple_sdk_gen/supplements/data/darwin_macos_26.5.md)

To extract comparison data from an installed SDK locally:

```sh
python3 tools/extract-darwin-libs.py "$REFERENCE_SDK" \
  --platform macos --output "$LOCAL_METADATA"
```

To audit the four generated Darwin stubs against a local Xcode SDK:

```sh
python -m tools.apple_sdk_gen.compare_darwin_stubs \
  "$REFERENCE_SDK" "$GENERATED_SDK" --report-only > darwin-coverage.json
```

The release workflow also compares against the preceding published archive
for the same SDK version. It blocks removals and changes of export kind or
reexport path. An intentional removal needs an exact entry in
`tools/darwin-removals/<baseline-tag>.tsv` with a source or rationale.
The tab-separated columns are `stub`, `provider`, `kind`, `name`, and `reason`.
Use the fields in the comparison report to identify an entry.

## CI and limitations

Pushes to `main` and pull requests run the unit tests. The manual
**Release** workflow packages the macOS SDK on an Apple Silicon runner.

The [known limitations](tools/apple_sdk_gen/LIMITATIONS.md) describe
framework APIs that need evidence beyond Apple’s documentation.

## Composed macOS SDK

The HermeticBuild release can also build a standalone arm64 macOS 26.5
`MacOSX.sdk.tar.zst`. It builds C and Objective-C runtime headers from the
locked C SDK source checkout, then adds generated and Apple OSS frameworks
and link stubs. See the [composed release build](release/README.md) and
[consumer tests](e2e/README.md).
