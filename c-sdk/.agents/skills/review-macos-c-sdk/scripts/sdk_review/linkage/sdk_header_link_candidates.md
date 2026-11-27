# SDK C-header linker candidates

Run from the repository root with a locally installed Apple macOS SDK and
the [verified official LLVM bundle](../../../../../../tools/toolchain/README.md).

    python3 -m sdk_review.linkage.sdk_header_link_candidates \
      --sdk "$(xcrun --sdk macosx --show-sdk-path)" --llvm "$LLVM" \
      --out "$WORK/c-header-candidates.json" --jobs 4

The survey registers each logical `usr/include/**/*.h` path independently
with Clang InstallAPI in C mode with Blocks at macOS 11.0. It repeats the scan
for arm64 and x86_64. Headers reached through an in-SDK directory alias keep
their logical path. The report lists the symlink and the canonical file.
The SDK's `usr/include/c++/` tree and links into framework trees are recorded as
exclusions. Repeat `--header usr/include/example.h` to reproduce specific cases.
Each invocation uses disposable working files. `--timeout` controls the
per-header process deadline.

Read `rows` for the selected root and target. `exported` indicates at least one
InstallAPI export, `zero-export` records a successful empty result, and `failed`
preserves the diagnostic for that particular C include context. Names are the
TBD spellings, with the encoding and separate weak, TLS and segment attributes.
The SDK build, verified LLVM lock digest, alias ledger and per-target status
counts support comparisons. `module_map_links` lists the direct lexical link
directives with file and line. Those directives are separate observations from
the per-header symbol candidates.

Join candidate names by architecture and encoding to the SDK TBD index to
identify possible providers. Header declarations alone leave provider
selection, reexports, ambiguous matches, symbol availability and linker
behavior to that independent comparison. Inline code and macros may generate
imports that InstallAPI cannot see here. A failed direct context may work via
its umbrella header or under another language or feature profile. Keep this
SDK-reference output local and outside the release inputs.
