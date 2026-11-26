# Build the full macOS 26.5 SDK

On an arm64 Mac with the Xcode command line tools, use Python 3.12+, CMake,
Ninja, zstd, and gh. Install the SDK Gen Python dependencies with
`python3 -m pip install -e tools/`. Check out
[apple-oss-c-sdk](https://github.com/hermeticbuild/apple-oss-c-sdk) at the
commit in [c-sdk.commit](c-sdk.commit). The build invokes C and objc4 Make
targets in that checkout.

```sh
mkdir -p build
(cd build && shasum -a 256 -c ../release/replay-inputs.sha256 && tar -xf replay-inputs.tar.zst)
release/build-composed-sdk.sh /path/to/apple-oss-c-sdk build/replay-inputs build/sdk
release/test-composed-sdk.sh /path/to/apple-oss-c-sdk build/sdk
```

Output is `build/sdk/MacOSX.sdk.tar.zst`, which also supplies the existing
[Bazel workspaces](../e2e/README.md). For local replays, point `C_SOURCE_CACHE`,
`LLVM_CACHE`, `LIBCXX_CACHE`, and `FRAMEWORK_SOURCE_ROOT` at existing caches.
`LLVM_DIR` selects an already verified official LLVM projection.

## Replay inputs

The byte-preserving migration uses a pinned `replay-inputs.tar.zst` containing
these SDK Gen outputs.

| Path | Origin |
|---|---|
| `frameworks/` | Extracted predecessor SDK with SHA-256 `ae7068d01df98b261a54216ec1482477934c3c1bf6bfd2f2767c17412733b8da`. The build reads its frameworks, SIMD headers, libz stub and version metadata. |
| `Foundation.tbd` | Generated SDK Gen 26.5 Foundation stub, before the local Foundation patches. Its SHA-256 is pinned in the Foundation Makefile. |
| `CoreGraphics.framework/` | Generated 26.5 bundle before the local geometry-header patch. |
| `CoreServices.tbd` | Generated 26.5 CoreServices stub passed to the existing CoreServices recipe. |
| `generated/SDKSettings.json` | The generated arm64 26.5 settings from the baseline Darwin input. |

Cocoa’s existing recipe reads commit
`0d09d30194aad45f292d9759f49bb19b8aab069f` from SDK Gen Git history.
Fetch the `cerisier/cocoa-umbrella` branch if a local checkout lacks that
commit. See [composition licensing](../docs/composition-licensing.md) for
the inherited distribution questions.

The expected full SDK SHA-256 using zstd 1.5.7 is
`e1b32d42efb158d0a51d4c1ad43f4941fa4533f1eda3f82cb4409cc73724cd9a`.

## GitHub Actions

The manual **Build composed macOS SDK** workflow checks out the C producer
with `C_SDK_READ_TOKEN`, reads the replay asset from the given release or
draft in the SDK Gen repository, builds both projects, runs the local probes,
and uploads the archive as a workflow artifact. On main, an optional
existing draft release tag attaches the composed SDK to that draft.
The existing **Release** workflow still emits the Xcode-shaped archive.
The C repository has its own manual workflow for the standalone C archive.
