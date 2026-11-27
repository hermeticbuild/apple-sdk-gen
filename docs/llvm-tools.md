# LLVM tools for building the SDK

`make prepare-llvm` fetches the official macOS ARM64 LLVM 21.1.6 archive
and verifies its pinned SHA-256 and GitHub attestation. The release pin
lives in [llvm-macos-arm64.json](../tools/apple_sdk_gen/supplements/data/llvm-macos-arm64.json).

The prepared directory contains Clang, its resource headers, InstallAPI,
LLD, Mach-O inspection tools, Darwin builtins, and the C++ headers. It
defaults to `build/inputs/llvm`. Pass `LLVM_DIR` to Make to select a
different directory. `OFFLINE=1` uses the prepared directory or the local
archive, attestation, and trusted root in `build/inputs/downloads`.

SDK Gen copies libc++ and libc++abi headers from the same archive. Its
[configuration patch](../tools/apple_sdk_gen/supplements/data/libcxx-apple-config.patch)
applies LLVM's Apple preset choices for vendor availability annotations
and the libdispatch backend for parallel algorithms. The two license
files are from the corresponding directories at LLVM's `llvmorg-21.1.6` tag.

When changing the compiler pin, run `make test-llvm-tools` to exercise
InstallAPI, Mach-O imports, LLD, and the bundled Darwin builtins.
