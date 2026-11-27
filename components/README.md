# Header recipes

The root Makefile orders producer staging, the pre-MIG merge, both MIG runs,
their comparison, and final assembly. Each producer adds a dependency to
the Make target named `stage` and stages files in its own directory.
`make install` supplies a fresh work directory and removes it on exit. The selected source tree is passed as `SOURCE_ROOT`.
Receipts name source inputs as `sources/<project>/...`. The merger resolves
these logical paths under `SOURCE_ROOT` and copies the selected lock into the
finished installation.

Each producer owns its Makefile, patches, templates, flags, and generator
scripts. Makefiles call Apple's pinned install rules where possible.
Apply each compatibility patch to the producer's staged files before recording
provenance. A patch preamble records the pinned source, affected SDK and targets,
reason for the edit, and supporting evidence. CarbonHeaders patches its headers
after Apple's install rule. AvailabilityVersions patches a staged copy of the
DSL before generation and adds the xros aliases to its output. XNU uses that same
staged DSL. Apple's source checkouts remain clean.

A stage has a `dst/usr/include` tree and a tab-separated `records` file.
Every file has one record with its installed path, owner, origin, selection,
transform, and one or more repo-relative input paths. Direct copies and
generators write those records as they stage their output. The
`record-installed.sh` helper enumerates public headers written by Apple
install scripts in a subtree named by the owning recipe.

`merge.sh` compares each stage's files with its records, checks paths and
collisions, and installs into a temporary tree. The pre-MIG operation
publishes just that tree. The final operation batch-hashes the headers and
writes a single path-sorted `header-manifest.tsv`. Each row begins with the
installed path and SHA-256, followed by the remaining producer fields.
The last field in the column header, `inputs...`, denotes one tab-separated
field per input path. The arm64 MIG stage supplies the public Mach headers.

The Libm recipe includes the input-denormal exception in `FE_ALL_EXCEPT`.
XNU's `FPSR_IDC` supplies bit 7 and
LLVM libc's Darwin implementation confirms the `FE_FLUSHTOZERO` spelling.
Pinned Apple Libm supplies the five standard exception bits. The local
`FE_FLUSHTOZERO` definition adds no linker symbol.
[XNU FPSR bits](https://github.com/apple-oss-distributions/xnu/blob/xnu-12377.121.6/osfmk/arm64/proc_reg.h#L815-L826)
· [LLVM libc Darwin fenv](https://github.com/llvm/llvm-project/blob/llvmorg-23.1.2/libc/src/__support/FPUtil/aarch64/fenv_darwin_impl.h#L61-L72)

The XNU recipe runs the pinned public install rules for selected components
through [install.mk](xnu/install.mk). Apple Make selects the headers, resolves
the Mach assembler inputs through VPATH, and filters public output with
`unifdef` and a comment-only check. Small Perl and shell helpers supply the
empty-file check and the Make stamp without compiling host utilities.
The recipe also uses the Libsyscall public MIG list
and upstream attribute filter. XNU generates
`sys/syscall.h` from `bsd/kern/syscalls.master`. The public macOS 26.5
source leaves syscall number 519 unassigned, while Xcode 26.5 names it
`SYS_register_uexc_handler`. The installation keeps the public XNU output.
The recipe also installs the userspace branch of `libkern/os/log.h` for
compiler-rt. Apple omits this header from the public userspace install
list. Apple SDK Gen 0.0.4 copies the same pinned XNU source directly.

The syslog recipe copies `asl.h` from the pinned syslog project's public
header phase. Use the [SDK review skill](../.agents/skills/review-macos-c-sdk/SKILL.md)
for reference comparisons and gap investigations.
