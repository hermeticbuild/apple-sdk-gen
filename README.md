# apple-sdk-gen

Generate an arm64 macOS SDK for C, C++, Objective-C and Objective-C++.
Framework declarations come from Apple’s public documentation. Clang
module maps and linker stubs make the generated interfaces usable by
cross-compilers.

## Generate macOS 26.5

On arm64 macOS with Python 3.12 or newer, prepare LLVM and generate the SDK.

```sh
python3 -m pip install -e tools/
make prepare-llvm
python3 -m tools.apple_sdk_gen --sdk-version 26.5 \
  --frameworks Cocoa,CoreFoundation,CoreGraphics,Network,Security \
  --llvm-dir build/inputs/llvm --cache-dir cache --output output
```

The SDK is at
`output/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk`.
The cache stores DocC responses for regenerating frameworks. Selecting
Cocoa requests Foundation, AppKit and Core Data and builds their umbrella.

| Flag | Purpose |
|---|---|
| `--sdk-version` | Required version of the generated SDK |
| `--darwin-library-metadata` | Override the bundled 26.5 inventory with a matching version |
| `--frameworks` | Generate a comma-separated set of frameworks |
| `--exclude-frameworks` | Exclude selected frameworks, including Cocoa |
| `--llvm-dir` | Install C++ and ABI headers from a prepared LLVM directory |
| `--output`, `--cache-dir` | Choose the SDK output and download cache directories |
| `--concurrency`, `--rate-limit` | Set the DocC request limits |
| `-v`, `-vv` | Enable info or debug logging |

The C++ layer uses the official LLVM 21.1.6 binary release, matching the
libc++ version reported by Xcode 26.5. The installer applies LLVM's Apple
preset choices to `__config_site` and includes both upstream license
files. Consumers link to the macOS system dylibs. Pass the directory from
`make prepare-llvm` with `--llvm-dir`. The full release includes C++ headers.
[LLVM release](https://github.com/llvm/llvm-project/releases/tag/llvmorg-21.1.6)

Selecting Model I/O or supplying `--llvm-dir` generates `<simd/simd.h>` and a
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

## CI and limitations

Pushes to `main` and pull requests run the unit tests. The manual
**Release** workflow packages the macOS SDK on an Apple Silicon runner.

The [known limitations](tools/apple_sdk_gen/LIMITATIONS.md) describe
framework APIs that need evidence beyond Apple’s documentation.

## Composed macOS SDK

The HermeticBuild release builds a standalone arm64 macOS 26.5
`MacOSX.sdk.tar.zst`. It builds C and Objective-C runtime headers from the
locked C SDK source checkout, then adds generated and Apple OSS frameworks
and link stubs. See the [composed release build](release/README.md) and
[consumer tests](e2e/README.md).
