# LLVM tools for building the SDK

`make prepare-llvm SDK=macosx26.5` fetches the official macOS ARM64 LLVM 21.1.6 archive
and checks its pinned SHA-256. The release pin
lives in [macosx26.5.json](../locks/macosx26.5.json).

The prepared directory contains Clang, its resource headers, InstallAPI,
LLD, Mach-O inspection tools, Darwin builtins, and the C++ headers. It
defaults to `build/inputs/llvm`. Pass `LLVM_DIR` to Make to select a
different directory. `OFFLINE=1` uses the prepared directory or the local
archive in `build/inputs/downloads`. Reusing a prepared directory checks
its archive SHA-256 receipt. Treat the prepared directory as read-only.

SDK Gen copies libc++ and libc++abi headers from the same archive. Its
[configuration patch](../tools/apple_sdk_gen/supplements/data/libcxx-apple-config.patch)
applies LLVM's Apple preset choices for vendor availability annotations
and the libdispatch backend for parallel algorithms. The two license
files are from the corresponding directories at LLVM's `llvmorg-21.1.6` tag.

When changing the compiler pin, run `make test-llvm-tools SDK=macosx26.5` to exercise
InstallAPI, Mach-O imports, LLD, and the bundled Darwin builtins.
