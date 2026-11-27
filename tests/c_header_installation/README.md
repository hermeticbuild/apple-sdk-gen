# C installation tests

Run from the repository root with the generated C installation and the
same pinned Clang used by `make install`.

```sh
make test SDK="$SDK" CLANG="$LLVM_CLANG" OUT="$C_INSTALL"
```

- `test_xnu_install.py` checks installed XNU headers and their source receipts.
  `test_merge_stages.py` exercises how staged headers are combined.
- `compile_probes.py` compiles each include root in
  `default_profile.c` individually, then compiles the full
  probe and the fixtures selected by Make. It targets macOS 14 for arm64
  with C11, using the installation and Clang resource headers.
- The fixture list in Make is explicit. The 26.5-specific availability and
  binary16 function signature cases only run for the 26.5 installation.
  The separate [binary16 runtime procedure](../../.agents/skills/review-macos-c-sdk/scripts/sdk_review/headers/half_math_runtime.md)
  compiles a client object, links it and executes it on macOS.
- The arm64 macOS runtime check calls host libSystem to verify the 16-byte
  floating-point environment layout and FPCR rounding bits. It reports a skip
  on other hosts. The compile fixture checks the installed declaration.
