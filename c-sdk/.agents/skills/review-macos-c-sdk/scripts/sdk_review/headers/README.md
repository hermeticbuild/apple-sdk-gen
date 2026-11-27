# SDK coverage review

Run this workflow when qualifying a new SDK version, updating Apple OSS pins,
or investigating a scope gap. It reads the SDK and the generated installation
and writes review reports. The Make installer has no dependency on the SDK
or these ledgers.

Start with the [skill instructions](../../../SKILL.md).

## Compare coverage with an official SDK

Use `make -f .agents/skills/review-macos-c-sdk/headers.mk paths` with the
inputs from the skill. That target traces the shipping probe against each
sysroot and inventories all of the SDK's `usr/include`. The `discovery`
target traces the extra roots in report-only mode. For a direct comparison
on arm64, pass `--reference "$WORK/reference.json"` to
`sdk_review.headers.trace_includes` when tracing the installation.

With the import path from the skill, rerun the path audit in strict
decision mode after the `paths` target.

```sh
python3 -m sdk_review.headers.audit_sdk_headers \
  --sdk "$APPLE_SDK" --installation "$C_INSTALL" --clang "$LLVM/bin/clang" \
  --reference "$WORK/reference.json" --generated-probe "$WORK/generated.json" \
  --baseline "$REVIEW/scripts/sdk_review/headers/data/macosx26.5/inventory.json" \
  --require-decisions --out "$WORK/header-audit.json" --review-out "$WORK/header-review.md"
```

The baseline records the SDK metadata, ordered paths, and their digest.
The [full historical report](https://github.com/hermeticbuild/apple-oss-c-sdk/blob/b308386/tools/sdk_review/inventories/macosx26.5.json)
stays available in Git history. Ledgers are selected by the reference SDK's
canonical name. A new version begins without approvals. Regenerate closures
when changing the probe or compiler.

The shipping trace and paired interface compile use macOS 14.0. Set
`MINIMUM` to change the census and complex runtime targets, which default
to 11.0.

| Input | Meaning |
| --- | --- |
| [Header decisions](data/macosx26.5/sdk-header-decisions.tsv) | Pattern, include or omit decision, reason, evidence, SDK name, and digest of the approved matching paths |
| [Review notes](data/macosx26.5/sdk-review-notes.tsv) | Outstanding source gaps |
| [Scope approvals](data/macosx26.5/sdk-scope-approvals.tsv) | Approved sets outside the package scope |
| [Installation-only decisions](data/macosx26.5/installation-only-decisions.tsv) | Reviewed generated paths absent from the SDK |
Installed headers record their current source selections in the generated
manifest. See the [recipe documentation](../../../../../../recipes/README.md).

### Outstanding discovery coverage

The 26.5 discovery trace reaches 16 `simd/*` and 11 `xpc/*` paths approved
for omission while a simple public Apple OSS source is unavailable. It also
reaches all 15 legacy RPC service headers approved for omission. Apple OSS
Librpcsvc can generate those headers for consumers that need them.
Clang's resource `tgmath.h` fallback makes the shipping probe compile. SDK
`tgmath.h` API parity remains open. See the [source findings](data/macosx26.5/header-source-candidates.md).

The broad trace also found seven CoreFoundation framework gaps outside the
`usr/include` inventory. They are `CFAttributedString.h`, `CFCGTypes.h`,
`CFFileDescriptor.h`, `CFFileSecurity.h`, `CFNotificationCenter.h`,
`CFStringTokenizer.h`, and `CFURLEnumerator.h`. The pinned CF tree lacks those
headers. Historical swift-corelibs-foundation sources provide leads for
`CFAttributedString.h` and `CFNotificationCenter.h`, but its
[Swift 5.0 build script](https://github.com/swiftlang/swift-corelibs-foundation/blob/swift-5.0-RELEASE/build.py)
does not distinguish their public install status, and the latter header's
enum macros are incompatible with our pinned CF headers.

The discovery probe excludes five public architecture headers that failed at
least one target even against SDK 26.5: `architecture/alignment.h`,
`architecture/i386/pio.h`, and `architecture/arm/{asm_help,cframe,reg_help}.h`.
Apple's pinned `architecture/Makefile:copyhdrs` still installs all 19 public
headers.

Each saved closure records the probe's exact digest. Regenerate discovery
closures after updating the fixture. Generate current review Markdown with
`audit_sdk_headers --review-out`.

## Compare with Apple SDK Gen

For an investigation of overlaps and differences with Apple SDK Gen, run
`compare_sdk_gen_headers.py`. It reports path differences, byte-identical
matches and differences, and absent paths supplied by Clang. It also compares
CoreFoundation header trees when available.

```sh
python3 -m sdk_review.headers.compare_sdk_gen_headers \
  --c-root "$C_INSTALL" --reference-sdk "$SDK_GEN" --clang "$LLVM/bin/clang"
```

## Test the review helpers

```sh
make -f "$REVIEW/headers.mk" test LLVM="$LLVM"
```
