# macOS 26.5 Darwin export inventory

`darwin_macos_26.5.json` is the bundled arm64 inventory for macOS 26.5.
Generate its stubs with:

```sh
python3 -m tools.apple_sdk_gen --sdk-version 26.5 \
  --frameworks CoreGraphics,Network,Security
```

The source-backed export selection uses:

- [Apple's macOS 26.5 source distribution](https://github.com/apple-oss-distributions/distribution-macOS/tree/83390100289cedfe669c31a96c94326d31afa1ed).
  Use the C installation produced from this release. Compile references
  for the public headers with pinned Clang and inspect their undefined
  Mach-O symbols. Use the published
  [Libsystem component selection](https://github.com/apple-oss-distributions/Libsystem/blob/c23b51183e46e613375dc7639fb4bf11fbf59ba8/xcodescripts/linker_arguments.sh)
  and verified providers on macOS 26.5.2 build 25F84. The supplemental
  source evidence covers Libc's forwarding, stack and fortify symbols,
  the XNU syscall and MIG interfaces, dyld's assembly, libunwind,
  CommonCrypto, and Libnotify. The emitter retains 40 library
  documents with their target-specific exports and reexports.
- [objc4 at the matching distribution pin](https://github.com/apple-oss-distributions/objc4/tree/ebfe77e64331034c867285a95d3ac205203291d5).
  Extract public declarations with clang-installapi. Also qualify the
  compiler ABI from the published objc4 declarations and
  [Clang's ARC specification](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/clang/docs/AutomaticReferenceCounting.rst)
  and code generation. Retain the matching deployed exports.
  Clang emits a reference to `__objc_empty_cache` for Objective-C class
  definitions. Pinned
  [objc4 source](https://github.com/apple-oss-distributions/objc4/blob/ebfe77e64331034c867285a95d3ac205203291d5/runtime/objc-cache.mm#L215-L231)
  defines it as global data and both deployed runtime slices export it.
  An AppKit delegate class linked and ran on each target through this export.
  Objective-C code that sends a message to `super` and synthesizes an
  atomic retained property also imports `objc_msgSendSuper2`,
  `objc_getProperty`, and `objc_setProperty_atomic`. The pinned
  [arm64 messenger assembly](https://github.com/apple-oss-distributions/objc4/blob/ebfe77e64331034c867285a95d3ac205203291d5/runtime/Messengers.subproj/objc-msg-arm64.s#L683-L699)
  and [property accessors](https://github.com/apple-oss-distributions/objc4/blob/ebfe77e64331034c867285a95d3ac205203291d5/runtime/objc-accessors.mm)
  define all three, and the installed macOS 26.5.2 runtime exports them
  from `/usr/lib/libobjc.A.dylib`. The OpenCV Cocoa backend imports
  them through compiler-generated code.
- [LLVM 23.1.2 Darwin libc++ ABI lists](https://github.com/llvm/llvm-project/tree/85ac560262434c9ccfc0c183ec22d4138ed647fb/libcxx/lib/abi)
  and [libc++abi export lists](https://github.com/llvm/llvm-project/tree/85ac560262434c9ccfc0c183ec22d4138ed647fb/libcxxabi/lib).
  Retain symbols present in the selected ABI and the corresponding
  deployed export table. Preserve verified symbol reexports and weak
  exports.

GNU Make uses the POSIX process environment directly. Apple's pinned
[dyld implementation](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/libdyld/libdyldGlue.cpp#L1206-L1212)
defines the `environ` data object. Both deployed slices export it from
libdyld. A C client linked through libSystem and read the same environment
as `_NSGetEnviron()` at deployment minima 11.0 and 26.5 on both CPUs.

Apple Libc builds out-of-line character classification and conversion
functions through [isctype.c](https://github.com/apple-oss-distributions/Libc/blob/4e34d0559e3a1b081afeb8604d9e204a1f31321d/locale/isctype.c).
Run clang-installapi over the installed `_ctype.h` with
`-D_DONT_USE_CTYPE_INLINE_` to obtain the client declarations for both
targets. The 23 names exported by each deployed libsystem_c slice are
also in Xcode 26.5. Two extra header declarations, `_tolower` and
`_toupper`, have macro implementations in the ordinary header mode
and have no matching runtime export. A client forced to use real
external references ran at deployment minima 11.0 and 26.5 on both CPUs.

The arm64 preview also includes the compiler-rt bindings previously
qualified for the C SDK. The installed macOS 26.5.2 runtime confirms the
names in each provider. A single arm64 client referencing all 21
symbols links through libSystem with the same Mach-O import names and
owners as the Xcode 26.5 comparison at deployment minima 11 and 26.5.
The C installation continues to ship its public headers.

| Provider | Source of the linker names |
| --- | --- |
| libsystem_kernel | [XNU's syscall table](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/bsd/kern/syscalls.master) and [Libsyscall fork assembly](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/libsyscall/custom/__fork.s) |
| libsystem_malloc | [libmalloc's zone globals and implementation](https://github.com/apple-oss-distributions/libmalloc/blob/c49dafa25f1efe8607701ae6014a663ad2ee437f/src/malloc.c) |
| libdyld | [dyld's inspection declarations](https://github.com/apple-oss-distributions/dyld/blob/fd8d0c4d52320ebf64db34f3cb280310d905c5ae/include/mach-o/dyld_priv.h) |
| libdispatch | [libdispatch's Mach interface](https://github.com/apple-oss-distributions/libdispatch/blob/701f4d1a24ae9c6863901bbbb22624b7d1b87321/private/mach_private.h) |
| libsystem_platform | [libplatform's lock interface](https://github.com/apple-oss-distributions/libplatform/blob/b7ed7cf5cf7dd12b98672435db2225a860f199d8/private/os/lock_private.h) and [ucontext implementation](https://github.com/apple-oss-distributions/libplatform/tree/b7ed7cf5cf7dd12b98672435db2225a860f199d8/src/ucontext) |
| libsystem_c | Libc's [realpath](https://github.com/apple-oss-distributions/Libc/blob/4e34d0559e3a1b081afeb8604d9e204a1f31321d/stdlib/FreeBSD/realpath.c) and [fileno](https://github.com/apple-oss-distributions/Libc/blob/4e34d0559e3a1b081afeb8604d9e204a1f31321d/stdio/FreeBSD/fileno.c) |

The arm64 `libc++abi.tbd` also includes the four direct exports from
[LLVM 21.1.6's Darwin export list](https://github.com/llvm/llvm-project/blob/a832a5222e489298337fbb5876f8dcaf072c5cca/libcxxabi/lib/symbols-not-reexported.exp).
LLVM's CMake rules export the three RTTI objects and the primary-exception
routine from libc++abi. The installed 26.5.2 dylib confirms all four as
strong exports. The ASan and UBSan comparison links bind them directly
to `/usr/lib/libc++abi.dylib` with Xcode 26.5.

The arm64 inventory uses provider evidence from the arm64e runtime.
Xcode 26.5 is a comparison reference. The arm64 C, Objective-C ARC
and C++ probes link against the inventory. `pipe` links and runs.
`pipe2` and `dup3` are absent from this SDK version.

Apple documents [`xpc_date_create_from_current`](https://developer.apple.com/documentation/xpc/xpc_date_create_from_current%28%29?language=objc)
as available since macOS 10.7. The arm64e export table of the installed
macOS 26.5.2 (25F84) image lists `_xpc_date_create_from_current` as a
strong export of `/usr/lib/system/libxpc.dylib`. A standalone arm64 C
client targeting macOS 11 links through `libSystem` and runs on that OS.
