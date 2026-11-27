# macOS 26.5 arm64 fpclassify linkage gap

**C client fixed.** On macOS arm64 the installed C header now inlines
Apple's integer implementation from the pinned
[ARM fpclassify.c](https://github.com/apple-oss-distributions/Libm/blob/17a5f9daa3f5679f7536b26f133b40cc078753c3/Source/ARM/fpclassify.c)
for binary64. This preserves the original float dispatch. Apple OSS
supplies the algorithm; using it inside the public C header is our
reviewed derivation. The macro evaluates its argument once and handles a
signaling NaN without raising `FE_INVALID`. A tested alternative based on
`__builtin_fpclassify` raised that flag. Reopen this packaging choice if
Apple publishes a matching arm64 public header. The original Apple header's
linker spelling is a separate provenance question.

**Baseline.** A C client compiled against the previous generated `math.h` with
`fpclassify(double)` or `fpclassify(long double)` imports `___fpclassify`
on macOS arm64. Both linkers report that symbol undefined against SDK
26.5 build 25F70. The SDK header emits `___fpclassifyd` for both input
types, which have the same size in this ABI.

| Client architecture | Input type | Generated object and SDK link | Reference object and SDK link |
| --- | --- | --- | --- |
| arm64 | `float` | `___fpclassifyf`, bound | `___fpclassifyf`, bound |
| arm64 | `double` | `___fpclassify`, undefined | `___fpclassifyd`, bound |
| arm64 | `long double` | `___fpclassify`, undefined | `___fpclassifyd`, bound |
| x86_64 | `float` | `___fpclassifyf`, bound | `___fpclassifyf`, bound |
| x86_64 | `double` | `___fpclassifyd`, bound | `___fpclassifyd`, bound |
| x86_64 | `long double` | `___fpclassify`, bound | `___fpclassifyl`, bound |

This matrix used LLVM 23.1.2 at `-O0` and `-O2`, deployment minima
11.0 and 26.5, and both `ld64.lld` and Xcode 26.5's `ld`. Successful
executables bound through libSystem and classified zero, subnormal,
normal, infinity and NaN correctly on macOS 26.5.2 build 25F84 using
native arm64 and Rosetta x86_64.

## Apple OSS search

- The latest published Libm tag, `Libm-2026` at
  `17a5f9daa3f5679f7536b26f133b40cc078753c3`, declares
  `__fpclassify(double)` in its ARM header and exports the old spelling
  from its ARM build. The Intel and PowerPC branches declare
  `__fpclassifyd(double)`. The public Libm tags and history contain no
  `__fpclassifyd` occurrence in the ARM source or common math header.
  [ARM header](https://github.com/apple-oss-distributions/Libm/blob/17a5f9daa3f5679f7536b26f133b40cc078753c3/Source/ARM/math.h#L127-L134) ·
  [ARM VFP exports](https://github.com/apple-oss-distributions/Libm/blob/17a5f9daa3f5679f7536b26f133b40cc078753c3/Exports/libm_arm_vfp.a.exp#L251-L253) ·
  [Intel header](https://github.com/apple-oss-distributions/Libm/blob/17a5f9daa3f5679f7536b26f133b40cc078753c3/Source/Intel/math.h#L123-L130) ·
  [PowerPC header](https://github.com/apple-oss-distributions/Libm/blob/17a5f9daa3f5679f7536b26f133b40cc078753c3/Source/PowerPC/math.h#L135-L142)
- In cctools, `otool/main.c` defines a placeholder that always returns
  zero in the private non-dynamic link path that avoids Libm.
  Libc's `gdtoa/_ldbl_util.c` calls the helper in working with
  double-double values. It includes `math.h` for declarations and uses
  members absent from its arm64 long-double layout.
  [cctools stub](https://github.com/apple-oss-distributions/cctools/blob/e0d56624eca2a76c2ace4c21850df9e666de4ca5/otool/main.c#L4821-L4853) ·
  [Libc consumer](https://github.com/apple-oss-distributions/Libc/blob/4e34d0559e3a1b081afeb8604d9e204a1f31321d/gdtoa/_ldbl_util.c#L24-L61) ·
  [Libc arm64 layout](https://github.com/apple-oss-distributions/Libc/blob/4e34d0559e3a1b081afeb8604d9e204a1f31321d/fbsdcompat/_fpmath.h#L73-L100)
- Search scope included all locked C source trees, the public Libsystem
  project at `c23b51183e46e613375dc7639fb4bf11fbf59ba8` and GitHub's
  indexed default branches across `apple-oss-distributions`. The indexed
  search for `__fpclassifyd` found the Libm, Libc and cctools results
  above. The broader `fpclassify` search also surfaced compiler builtin
  code and unrelated C library consumers, without a macOS arm64 mapping.
  Query with `gh api -X GET search/code -f q='__fpclassifyd org:apple-oss-distributions'`.
  [Libsystem](https://github.com/apple-oss-distributions/Libsystem/tree/c23b51183e46e613375dc7639fb4bf11fbf59ba8)

The original ARM source does provide an implementation of binary64
classification. It inspects the exponent and significand as integers.
The build preserves its body, renames the helper and gives it internal
linkage. The generated TBD needs no additional entry.

## Reproduce

From the repository root, set `LLVM` to the verified LLVM bundle,
`C_INSTALL` to the generated 26.5 C install, and `APPLE_SDK` to the
matching Xcode SDK. Compile each type separately to inspect its imports.

```sh
WORK=$(mktemp -d)
RESOURCE=$("$LLVM/bin/clang" -print-resource-dir)/include
for arch in arm64 x86_64; do
  for type in FLOAT DOUBLE LONG_DOUBLE; do
    for side in generated reference; do
      case "$side" in
        generated) root="$C_INSTALL" ;;
        reference) root="$APPLE_SDK" ;;
      esac
      artifact="$WORK/$arch-$type-$side"
      "$LLVM/bin/clang" --no-default-config -target "$arch-apple-macos11.0" \
        -isysroot "$root" -nostdinc -isystem "$RESOURCE" -isystem "$root/usr/include" \
        -std=c11 -O2 -fno-builtin -fno-stack-protector -DPROBE_"$type" \
        -c .agents/skills/review-macos-c-sdk/scripts/sdk_review/headers/fixtures/c_codegen/fpclassify.c -o "$artifact.o"
      "$LLVM/bin/llvm-nm" -uj "$artifact.o"
      if "$LLVM/bin/ld64.lld" -arch "$arch" -platform_version macos 11.0 26.5 \
        -syslibroot "$APPLE_SDK" -e _main "$artifact.o" -lSystem -o "$artifact"; then
        xcrun dyld_info -imports "$artifact"
        arch "-$arch" "$artifact"
      fi
    done
  done
done
```
