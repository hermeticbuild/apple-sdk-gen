# Distribution provenance review (2026-11-17)

This is a source and terms inventory for the prototype, not a legal clearance.

## Standalone C installation

The installer reads pinned Apple OSS source checkouts, Apple OSS build generators,
the arm64 `fenv.h` declaration in `recipes/libm/`, and documented compatibility
edits in `recipes/`. It reads no Xcode SDK or
Apple SDK Gen header. Apple's [APSL 2.0 text](https://opensource.apple.com/apsl/)
permits use and external distribution of covered source for commercial or
noncommercial purposes without a hardware condition in that license. It
requires retention of notices and the license text; distributing modifications
adds change notices and source availability duties. Apple's own page cautions
that the actual license is determined by each project's included license and
file header. For example, `Libm/Source/fenv.h` identifies APSL 1.1, so APSL
2.0 alone is not a sufficient inventory for this output.
The pinned cctools, hfs, and libunwind sources need the same
file-level review; libunwind's Mach-O `compact_unwind_encoding.h` identifies
Apache-2.0 with LLVM exception. No libunwind runtime API header is installed.

Before publishing generated headers: inventory the exact file-level licenses,
include their texts and notices, mark the modified Apple headers and make the
generation source available as required, and review the local `fenv.h`,
`TargetConditionals.h`, and dyld header edits. The current repository
only pins sources and records transformations; it does not yet package a
complete license bundle for a generated installation.
