# macOS SDK integration tests

Build the [composed SDK](../tools/sdk_composition/README.md) with
`release/build-composed-sdk.sh` from the repository root. Bazel reads
`build/sdk/MacOSX.sdk.tar.zst` directly. Bazel watches the archive file and
refreshes the SDK repository when it changes.

## Minimal macOS SDK

The `c-sdk` workspace reads `build/sdk/MacOSX-Minimal.sdk.tar.zst`. It compiles
SQLite's engine and shell from the registry's `sqlite3` module and runs an
on-disk transaction, reopen and integrity check. The executable loads
libSystem.

```sh
(
  cd e2e/c-sdk
  export USE_BAZEL_VERSION=9.3.2
  bazel --nohome_rc run --platforms=@llvm//platforms:macos_arm64 \
    --@llvm//config:macos_libcxx_headers=llvm \
    --run_under="$PWD/sqlite-smoke.sh" @sqlite3//:shell
)
```

The workspace patches the pinned hermetic-llvm link flags to remove its
implicit Foundation and libc++ dependencies for this C-only test. The
same defaults otherwise apply to C execution tools built by the toolchain.
See [the test-only patch](c-sdk/framework-free-link.patch).

## Stage 1 Clang

Run with Bazel 9.3.2 and a configured `remote_default` in your Bazel rc.
The shared [remote configuration](remote.bazelrc) selects Linux workers.
It builds a macOS Clang with the seed compiler.

```sh
(
  cd e2e/llvm-stage1
  export USE_BAZEL_VERSION=9.3.2
  bazel --bazelrc=../remote.bazelrc build --config=remote -c opt \
    --platforms=@llvm//platforms:macos_arm64 \
    --@llvm//toolchain:bootstrap_stage=stage1_from_source \
    --@llvm//config:macos_libcxx_headers=sdk @llvm//tools:clang
)
```

## Local consumer suites

Run from this directory on Apple Silicon macOS.

```sh
USE_BAZEL_VERSION=9.3.2 bazel test //:hermetic_llvm
USE_BAZEL_VERSION=9.3.2 bazel test //:rules_rs
```

Bazel fetches both pinned source trees and the child Bazel binaries. Each
upstream test workspace runs as its own root, with an SDK repository
override pointing to the extracted root-build archive. Each suite runs
on arm64 locally. Run `//:libomp` for a focused check of the SDK
handoff.

The LLVM suite includes the manual header-order checks and sanitizer
builds. The Rust suite excludes the all-platform target-triple matrix.
Run the [LCOV report-content check](coverage.md) separately.

## Bazel Central Registry consumers

The `bcr` module takes the same SDK archive and lets Bazel fetch c-ares and
curl from the registry. Run both tests locally on Apple Silicon.

```sh
(
  cd e2e/bcr
  export USE_BAZEL_VERSION=9.3.2
  bazel --nohome_rc test --platforms=@llvm//platforms:macos_arm64 \
    --@llvm//config:macos_libcxx_headers=sdk \
    --@curl//:ssl_lib=mbedtls //:framework_consumers
)
```

- c-ares compiles the macOS DNS configuration path against
  `SCNetworkConfiguration.h` and its reachability and CoreFoundation
  dependencies. The test initializes a resolver without issuing a query.
  [c-ares module](https://registry.bazel.build/modules/c-ares/1.34.9.bcr.1/)
- curl compiles and calls the macOS proxy initialization path using
  `SCDynamicStoreCopyProxies` and `CFRelease`. The test initializes and frees
  a curl handle without making a request. The registry's Mbed TLS option
  avoids the Security framework dependency of the default TLS configuration.
  [curl module](https://registry.bazel.build/modules/curl/8.21.0/)
