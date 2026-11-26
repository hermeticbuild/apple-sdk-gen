# Release the arm64 macOS 26.5 SDK

The manual [Release workflow](../.github/workflows/release.yml) generates
frameworks, Darwin stubs, and LLVM libc++ headers using this checkout. It
builds the C and objc4 header trees from the source commit recorded in
[c-sdk.commit](c-sdk.commit). The workflow uses `C_SDK_READ_TOKEN` for the
private C Git checkout. The generation step reuses cached DocC responses
without time-based expiry and saves the expanded cache before the build
and tests. To refresh DocC for a release series, generate with a separate
cache directory and use that cache for the next build.

The default dispatch builds the archive and runs the C, framework, and BCR
tests. Select `publish` on main to tag the tested commit and publish the
same `MacOSX.sdk.tar.zst` with its SHA-256 file. The
[C SDK repository](https://github.com/hermeticbuild/apple-oss-c-sdk) builds
its standalone header archive separately.

## Build and test locally

Use an arm64 Mac with the Xcode command-line tools, Python 3.12 or newer,
CMake, Ninja, zstd, and gh. Install SDK Gen with `python3 -m pip install -e
tools/` and check out the pinned C SDK source.

```sh
python3 -m tools.apple_sdk_gen --sdk-version 26.5 --all-frameworks \
  --include-cxx --reuse-docc-cache --cache-dir cache --output build/generated -v
generated=build/generated/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
release/build-composed-sdk.sh /path/to/apple-oss-c-sdk "$generated" build/sdk
release/test-composed-sdk.sh /path/to/apple-oss-c-sdk build/sdk
```

The [Bazel workspaces](../e2e/README.md) read
`build/sdk/MacOSX.sdk.tar.zst`. The build driver takes the generated tree
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

The compressed file can live in durable storage outside GitHub. To
restore it, decompress it as `cache.db` in a new cache directory and pass
that directory to `--cache-dir`. The release build fetches any missing
pages. LLVM source archives are cached separately by the generator in the
same directory and can be fetched again from their pinned release.

The earlier frozen input and archive checksums are [in Git history](https://github.com/hermeticbuild/apple-sdk-gen/tree/c66fa45/release).
The fresh build uses the framework outputs generated in the release job.
See [composition licensing](../docs/composition-licensing.md) for the
source and redistribution notes.
