# Composed SDK tests

Run the minimal SDK suite against an extracted `MacOSX-Minimal.sdk.tar.zst`.
The clients exercise DNS-SD, the resolver, iconv, zlib, BSM, IPsec and SIMD.
The macOS 11 link probe checks that libSystem links and that Foundation is
absent. On Apple Silicon, set `RUN=1` to execute the linked clients.

```sh
make -C tests/minimal_sdk_linking test CLANG="$LLVM_CLANG" SDK="$MINIMAL_SDK" RUN=1
```

Run the full SDK suite against the assembled framework tree. The clients
exercise Foundation, CoreGraphics, Security, Network and Model I/O, plus
Objective-C compiler imports and Objective-C++ modules.

```sh
make -C tests/full_sdk_frameworks test CLANG="$LLVM_CLANG" SDK="$FULL_SDK" RUN=1
```

Run `test-avrouting` and `test-metalkit` explicitly to investigate the
[known framework gaps](composition-gaps.md). The
[Bazel integration workspaces](../e2e/README.md) test the composed SDK archives.
