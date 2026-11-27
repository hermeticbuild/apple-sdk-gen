# apple-sdk-gen

Generate an arm64 macOS SDK for C, C++, Objective-C and Objective-C++.
Apple's open-source releases supply the C and Objective-C runtime headers.
Apple's public documentation and local recipes supply framework declarations.
Clang module maps and linker stubs make the SDK usable by cross-compilers.

## Use a released SDK

Download an archive from [Releases](https://github.com/hermeticbuild/apple-sdk-gen/releases).
For the full SDK, run `tar -xf MacOSX.sdk.tar.zst` and use the extracted
`MacOSX.sdk/` as your compiler's sysroot. To verify a release archive,
see the [attestation instructions](release/README.md).

## Build macOS 26.5 from source

Use an arm64 Mac with Xcode command-line tools, Python 3.12, and zstd.
The release build uses a pinned DocC snapshot. To fetch it, set up the
[private R2 access](release/README.md#keep-a-portable-docc-cache) and
install the AWS CLI, or place a copy of the snapshot in the local download cache.

```sh
make prepare SDK=macosx26.5 PYTHON=python3.12
make generate-sdk SDK=macosx26.5
make compose-sdk SDK=macosx26.5
make test-composed-sdk SDK=macosx26.5
```

`make prepare` fetches the pinned Apple OSS sources, LLVM tools and C++
headers, and the DocC snapshot, then prepares the Python environment.
`make generate-sdk` generates framework headers and linker stubs.
`make compose-sdk` builds the Apple OSS headers, generates SIMD headers
from the pinned DocC snapshot, applies the framework recipes, and
packages both sysroots. See the
[release build instructions](release/README.md) for offline builds and
framework selection.

### Output layout

The composed build produces two archives in `build/sdk/`.

| Archive | Contents |
| --- | --- |
| `MacOSX-Minimal.sdk.tar.zst` | Framework-free C sysroot with C and SIMD headers, system linker stubs, and source receipts |
| `MacOSX.sdk.tar.zst` | Full sysroot with C, Objective-C runtime, libc++ and libc++abi headers, system linker stubs, and frameworks |

Both archives extract to `MacOSX.sdk/`. The minimal archive includes
`source-lock.json` and `c-sdk-provenance.json`. Representative paths
from the full archive are shown below.

```text
MacOSX.sdk/
├── SDKSettings.json
├── header-manifest.tsv
├── System/Library/Frameworks/
│   └── Foundation.framework/
│       ├── Foundation.tbd
│       ├── Headers/Foundation.h
│       └── Modules/module.modulemap
└── usr/
    ├── include/
    │   ├── stdio.h
    │   ├── simd/simd.h
    │   ├── objc/objc.h
    │   └── c++/v1/
    │       ├── cxxabi.h
    │       └── vector
    └── lib/
        ├── libSystem.B.tbd
        ├── libSystem.tbd → libSystem.B.tbd
        ├── libc++.tbd
        └── libobjc.tbd
```

The intermediate output from `make generate-sdk` uses the Xcode layout.

```text
build/generated/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/
├── MacOSX.sdk/
└── MacOSX26.5.sdk → MacOSX.sdk
```

## Generate framework inputs from live DocC

For framework development, prepare the LLVM and Python inputs and run
the generator directly against Apple's public documentation.

```sh
make prepare-llvm prepare-python SDK=macosx26.5 PYTHON=python3.12
build/inputs/python/bin/python -m tools.apple_sdk_gen --sdk-version 26.5 \
  --frameworks Cocoa,Foundation,AppKit,CoreData,CoreFoundation,CoreGraphics,Network,Security \
  --llvm-dir build/inputs/llvm --cache-dir cache --output output
```

The SDK is at
`output/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk`.
This is the intermediate SDK tree for composition. The cache stores DocC
responses for regenerating frameworks. List any framework dependencies
you need. Cocoa's umbrella uses Foundation, AppKit and Core Data.

| Flag | Purpose |
|---|---|
| `--sdk-version` | Required version of the generated SDK |
| `--darwin-library-metadata` | Override the bundled 26.5 inventory with a matching version |
| `--frameworks` | Generate a comma-separated set of frameworks |
| `--exclude-frameworks` | Exclude selected frameworks, including Cocoa |
| `--llvm-dir` | Install C++ and ABI headers from a prepared LLVM directory |
| `--output`, `--cache-dir` | Choose the SDK output and download cache directories |
| `--reuse-docc-cache` | Reuse saved responses without expiring them |
| `--docc-cache-only` | Use saved responses without network requests |
| `--concurrency`, `--rate-limit` | Set the DocC request limits |
| `-v`, `-vv` | Enable info or debug logging |

The C++ layer uses the official LLVM 21.1.6 binary release, matching the
libc++ version reported by Xcode 26.5. The installer applies LLVM's Apple
preset choices to `__config_site`, backports LLVM's Apple availability
mappings, and includes both upstream license
files. Consumers link to the macOS system dylibs. Pass the directory from
`make prepare-llvm` with `--llvm-dir`. The full release includes C++ headers.
[LLVM release](https://github.com/llvm/llvm-project/releases/tag/llvmorg-21.1.6)
· [LLVM availability patch](https://github.com/llvm/llvm-project/pull/140072)

Both composed archives include `<simd/simd.h>` and its module map. If you
generate Model I/O directly and need those headers in the intermediate
tree, run the [SIMD component](components/simd/README.md) with the same DocC
cache and point its `--out` at that tree's `MacOSX.sdk` directory.

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

Pushes to `main` and pull requests run `make test-python`. The generator's
unit tests live in [its Python package](tools/apple_sdk_gen/tests). The manual
**Release** workflow packages the macOS SDK on an Apple Silicon runner.
See [SDK tests](tests/README.md) for the checks on each build output.
The [consumer tests](e2e/README.md) show how to use the archives with Bazel.

The [known limitations](tools/apple_sdk_gen/LIMITATIONS.md) describe
framework APIs that need evidence beyond Apple’s documentation.
