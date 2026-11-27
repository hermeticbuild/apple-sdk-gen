# Compare installed C interfaces

To isolate which differences originate in each header, run the following
audit against an existing source-locked installation.

```sh
python3 -m sdk_review.headers.isolate_header_differences \
  --installation "$C_INSTALL" --sdk "$APPLE_SDK" --clang "$LLVM/bin/clang" \
  --out "$WORK/isolated.json"
```

Clang preprocesses the same public include twice against the installation.
A virtual filesystem overlay supplies just the selected reference header for
the second pass. Each cell records whether both passes entered the header,
the digest of the preprocessed C, and the names of differing macros. The
matrix covers arm64, default C11 and `_DARWIN_C_SOURCE`, and
deployment minima 11.0, 14.0 and the reference SDK version. Preprocessing
failures and headers skipped by their umbrella stay visible. Matching
preprocessing applies to that configuration and measures neither diagnostics
nor linkage. Keep the report local with the reference audit results.

Use the generated C installation, the reference SDK for the same canonical
release and build, and the verified LLVM bundle. Run from the repository root.

```sh
python3 -m sdk_review.headers.compare_c_interfaces \
  --installation "$C_INSTALL" --sdk "$APPLE_SDK" --clang "$LLVM/bin/clang" \
  --out "$WORK/semantics.json"
```

The report verifies the manifest and every installed header, then accounts for
identical headers, divergent counterparts, and installation-only headers.
Every divergent counterpart gets a public include test. Check
`headers[].include_reached` for the actual per-side trace result, including when
an umbrella succeeds without including the changed header. The trace records
both the path used to include a symlink and its resolved target.

The two sides use the same Clang, resource headers, C11 with blocks,
an arm64 target, and deployment floor 14.0. The named C consumers
live in [fixtures/c_interfaces](fixtures/c_interfaces). `probe_differences`
lists target-specific mismatches for this matrix. The full diagnostics and
include traces live in `probe_details`. The compiler, resource-header,
manifest, source-lock, and SDK metadata identities appear at the top of
the report. Keep the report with review evidence outside the release package.

The report covers every installed path and the listed consumer cases. Run
the [SDK path audit](README.md) for missing SDK paths. A matching diagnostic
can be a control, and a passing syntax probe provides no link or runtime
evidence. Use the paired linker on the affected consumers before claiming
ABI or deployment compatibility.

## Qualify typed malloc backdeployment

Use the Apple Clang from the Xcode installation that supplied `APPLE_SDK`.
Upstream LLVM lacks `-ftyped-memory-operations`. Use the verified LLVM bundle
for `llvm-nm`.

```sh
make -f .agents/skills/review-macos-c-sdk/headers.mk malloc-backdeploy \
  APPLE_CLANG="$(xcrun --find clang)" APPLE_SDK="$APPLE_SDK" \
  LLVM="$LLVM" C_INSTALL="$C_INSTALL" WORK="$WORK"
```

On arm64, the probe checks behavior with typed operations enabled
and disabled. At macOS 13.0 it checks weak typed imports and strong untyped
fallbacks, and inspects the LLVM IR for null-guarded dispatch. It also checks
that the direct typed call is rejected at 13.0 and accepted at 14.0. At 14.0,
enabled clients import the typed functions strongly. Keep the object and IR
files in `WORK` with the other review evidence. These checks cover code
generation and do not execute on an older runtime.

## Check binary16 math at runtime

Use the [binary16 procedure](half_math_runtime.md) to compile an explicit
client object, inspect the imports, and run it on arm64.

## Qualify `Block.h` pointer bounds

Compile [the fixture](fixtures/c_codegen/block_pointer_bounds.c) with Apple
Clang in C11 mode using `-fblocks -fbounds-safety -Werror`. The default case
must compile. With `-DTEST_UNSAFE_RAW_RELEASE`, it must diagnose the unsafe
conversion. Run both cases against the generated headers and the reference
SDK on arm64.

## Inspect fpclassify linkage

Use the [macOS 26.5 fpclassify gap](data/macosx26.5/fpclassify-gap.md) for
the isolated float, double and long-double client links. The arm64 double and
long-double cases compile successfully and surface the gap at link time.

## Inspect logging macro lowering

The same logging macro can emit different imports after a header change.
Build the checked-in call once against each explicit sysroot and inspect the
undefined names. This is a targeted header investigation.

```sh
RESOURCE=$("$LLVM/bin/clang" -print-resource-dir)/include
for side in reference installation; do
  case $side in
    reference) root="$APPLE_SDK" ;;
    installation) root="$C_INSTALL" ;;
  esac
  object="$WORK/os-log-error-arm64-$side.o"
  "$LLVM/bin/clang" -target arm64-apple-macos14.0 -isysroot "$root" \
    -nostdinc -isystem "$RESOURCE" -isystem "$root/usr/include" \
    -std=c11 -fblocks -O2 -c .agents/skills/review-macos-c-sdk/scripts/sdk_review/headers/fixtures/c_codegen/os_log_error.c -o "$object"
  "$LLVM/bin/llvm-nm" -u "$object"
done
```
