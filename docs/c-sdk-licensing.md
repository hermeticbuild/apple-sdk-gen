# C SDK sources and notices

The C SDK archive records the SDK Gen commit and Apple OSS lock. The
header manifest names the source files, install rules, local patches
and transformations. The composition manifest records digests and
symlink targets. The C SDK provenance file identifies the source of each
stub and the pinned DocC pages used for SIMD.

The C header build uses pinned Apple OSS checkouts, upstream generators
and the compatibility edits in components/. The release denies reads of
Xcode SDK headers and module maps during generation. The build can use
the Mac's host tools, including MIG. SDK Gen generates the two SIMD
files from C-family DocC pages and its own module map writer. The
official SDK is a separate comparison input. The [system stub table](../tools/apple_sdk_gen/supplements/system_libs.py)
records its Xcode iOS SDK export data. This source contributes linker stubs.

Read the license carried by each header and its source. The archive
includes the pinned projects' license files, the LLVM exception from
the pinned libunwind tree, and APSL 1.1 for the older Libm and Libinfo
headers. The APSL 1.1 text comes from the [Apple OSS IOSerialFamily release](https://github.com/apple-oss-distributions/IOSerialFamily/blob/ed4bc21ffe5d80594cc3771ac6527ea62d50dc45/APPLE_LICENSE).
BSD, ISC and zlib terms also appear directly in the relevant headers.
Notices for the generated Mach interfaces are under usr/share/licenses/xnu/.
The component patches record modifications. Use the source commit
in c-sdk-provenance.json to locate the exact build rules and patches.

The [distribution notes](composition-licensing.md) also cover the terms
applicable to Xcode-derived stub data and documentation-derived content.
