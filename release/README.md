# Release the arm64 macOS 26.5 SDK

The manual [Release workflow](../.github/workflows/release.yml) generates
frameworks, Darwin stubs, and LLVM libc++ headers using this checkout. It
builds the C and objc4 header trees with the [in-tree C SDK](../docs/c-sdk-headers.md).
The SDK Gen commit pins both sets of build rules. The release job restores the exact private DocC
snapshot recorded in [docc.snapshot](docc.snapshot) and uses only that
snapshot for DocC responses. The workflow pins its GitHub actions, Xcode,
Bazel, Python, and [Python wheels](requirements.txt). GitHub manages the
macOS and Ubuntu runner images. The build logs record the image and its
CMake, Ninja, zstd, AWS CLI, and Bazelisk versions.

The default dispatch builds and tests both archives without publication.

- `MacOSX-Minimal.sdk.tar.zst` provides the framework-free C sysroot, its
  linker stubs and its [source receipts](../docs/c-sdk-licensing.md).
- `MacOSX.sdk.tar.zst` adds Objective-C, C++, and frameworks.

Both archives extract to `MacOSX.sdk/`. Each has its own SHA-256 file.
Select `publish` on main to publish the tested archives under the same tag.
The publish job verifies both archives and their checksums against the
shared `MacOSX.sdk.tar.zst.attestation.jsonl` bundle.

Verify a downloaded SDK against its accompanying bundle:

```sh
gh attestation verify MacOSX.sdk.tar.zst --repo hermeticbuild/apple-sdk-gen \
  --bundle MacOSX.sdk.tar.zst.attestation.jsonl \
  --signer-workflow hermeticbuild/apple-sdk-gen/.github/workflows/release.yml \
  --source-ref refs/heads/main
```

## Build and test locally

Use an arm64 Mac with the Xcode command-line tools, Python 3.12 or newer,
CMake, Ninja, zstd, and gh. Install SDK Gen with `python3 -m pip install -e
tools/` from this checkout.

```sh
python3 -m tools.apple_sdk_gen --sdk-version 26.5 --all-frameworks \
  --include-cxx --docc-cache-only --cache-dir cache --output build/generated -v
generated=build/generated/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
release/build-composed-sdk.sh "$generated" build/sdk
release/test-composed-sdk.sh build/sdk
```

The [Bazel workspaces](../e2e/README.md) read the corresponding archive under
`build/sdk/`. The build driver takes the generated tree
as an argument so local recipe iterations can reuse it. Use
`C_SOURCE_CACHE`, `LLVM_CACHE`, and `FRAMEWORK_SOURCE_ROOT` to reuse local
source caches. `LLVM_DIR` selects a verified LLVM projection.

## Keep a portable DocC cache

Store a completed cache as a compressed SQLite backup. The backup captures
committed responses even when SQLite uses its WAL file.

```sh
sqlite3 cache/cache.db '.backup docc-macos-26.5.db'
zstd docc-macos-26.5.db -o docc-macos-26.5.db.zst
```

Keep snapshots in a private R2 Standard bucket without object expiration.
Set repository Actions variables `DOCC_R2_ENDPOINT` and `DOCC_R2_BUCKET`
and the bucket-scoped secrets `DOCC_R2_ACCESS_KEY_ID` and
`DOCC_R2_SECRET_ACCESS_KEY`. The workflow verifies the full SHA-256 in
`docc.snapshot` before extracting the pinned object. For a local restore,
extract the snapshot as `cache.db` in a fresh `--cache-dir`.

To refresh DocC, generate separately with `--reuse-docc-cache` to fetch
missing pages. Use a fresh cache directory to refresh existing pages as
well. Upload the checked snapshot under a new dated key in
`macos/26.5/snapshots/`, then commit the full SHA-256 and key in
`docc.snapshot`. Existing releases retain their snapshot pin. The
generator downloads the pinned LLVM source archives as needed.

The earlier frozen input and archive checksums are [in Git history](https://github.com/hermeticbuild/apple-sdk-gen/tree/c66fa45/release).
The fresh build uses the framework outputs generated in the release job.
See [composition licensing](../docs/composition-licensing.md) for the
source and redistribution notes.
