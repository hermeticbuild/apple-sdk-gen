# LLVM toolchains for SDK generation

## Official LLVM 23.1.2 for composition and SDK review

The [release lock](data/llvm-official-macos-arm64.json) pins the Apple Silicon
host archive, its GitHub build attestation, and the digests of the selected
executables, resource headers and Darwin builtins. The qualification
exercises arm64 Darwin clients and the included arm64 builtins.

On an Apple Silicon Mac, run from the repository root. Cold preparation uses
Python 3, `curl`, `gh`, `zstd` and macOS `tar`. Allow about 1.4 GB of cache
space and a 1 GiB zstd decoding window.

```sh
LLVM_DIR=$(python3 -m tools.toolchain.official_llvm prepare \
  --cache "$LLVM_CACHE" --c-install "$C_INSTALL" --receipt "$WORK/llvm.json")
LLVM_CLANG="$LLVM_DIR/bin/clang"
RESOURCE_DIR=$("$LLVM_CLANG" -print-resource-dir)
```

Preparation verifies the compressed archive and attestation bundle hashes,
checks the GitHub attestation for the pinned LLVM release workflow, tag and
commit, then extracts the tool projection. The projection includes all Clang
resource headers and the packaged macOS builtins. Use the directory printed on
stdout as the tool root.

For a warm run, add `--offline` to `prepare`. The prepared directory is
rehashed before each probe. For offline preparation with an empty projection,
provide the following three files in `LLVM_CACHE`. An online preparation
materializes all three. To record the trusted root alone, run
`gh attestation trusted-root > "$LLVM_CACHE/github-attestation-trusted-root.jsonl"`
on a connected machine.

- `LLVM-23.1.2-macOS-ARM64.tar.zst`
- `LLVM-23.1.2-macOS-ARM64.tar.zst.jsonl`
- `github-attestation-trusted-root.jsonl`

```sh
python3 -m tools.toolchain.official_llvm verify --llvm-dir "$LLVM_DIR" \
  --c-install "$C_INSTALL" --receipt "$WORK/llvm-verified.json"
```

`verify` works on a relocated projection without the archive or network. Both
commands run the same smoke test. Clang AST and InstallAPI exercise a function,
TLS, an explicit assembler name and an inline definition. The v5 reader
extracts the target from an umbrella with an embedded child. LLD links the
client object with an empty sysroot. The Mach-O inspection checks the import
names, bind-through library and load commands. A separate arm64 link checks
static resolution of `___udivti3` from the bundled archive. The receipt uses
logical roots for the probe commands.

`--c-install` runs the additional check against the generated C installation
and its header manifest. The InstallAPI export and client object must agree on
`_stat` on arm64. Omit it for a standalone
bootstrap check. Use `--work-dir` with an existing directory to retain the
inputs and outputs under a fresh child directory.

## Minimal prebuilt Clang for header installation

`resolve_clang.py` compares hermetic-llvm's minimal toolchain release and host
archive digest against [the checked-in pin](data/llvm-minimal-prebuilt.json),
fetches that target through Bazel, and prints the Clang path to stdout. Use
that path for Make and the C probes.

Run from the repository root with Bazel available and `LLVM_REPO` pointing
to a hermetic-llvm checkout whose minimal toolchain index matches the pin.

```sh
LLVM_CLANG=$(python3 -m tools.toolchain.resolve_clang --llvm-repo "$LLVM_REPO")
```
