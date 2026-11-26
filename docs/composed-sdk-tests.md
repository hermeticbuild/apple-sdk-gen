# Composed SDK tests

Run the DNS-SD and resolver link probes against the composed tree.
On Apple Silicon, set `RUN=1` to execute
the probes. They exercise the DNS-SD name helper and the resolver's
initialization and cleanup without sending DNS queries.

```sh
make -C tests/composed_sdk test CLANG="$LLVM_CLANG" SDK="$NEW_SDK" C_SDK="$C_SDK" RUN=1
```

Use the separate framework suite for an expanded composition. The probes
exercise Foundation macros and public graphics, security, networking and
model APIs. The AVRouting check imports the public header for a class
which macOS exposes in its SDK and marks unavailable.

```sh
make -k -C tests/composed_sdk test-frameworks CLANG="$LLVM_CLANG" SDK="$NEW_SDK" C_SDK="$C_SDK" RUN=1
```

The [Bazel integration workspaces](../e2e/README.md) test the composed SDK archive.
