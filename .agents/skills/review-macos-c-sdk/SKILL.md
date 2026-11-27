---
name: review-macos-c-sdk
description: Review a generated macOS C header installation against an official SDK, qualify a source-lock update, or investigate a missing header, declaration, or linker symbol.
---

# Review the macOS C SDK

Run from the repository root. Use a standalone installation built from the
selected source lock, the official SDK with the same version and build, and
the [pinned LLVM projection](../../../tools/toolchain/README.md). Keep the
reference SDK and generated review reports local.

```sh
make -f .agents/skills/review-macos-c-sdk/headers.mk -j3 header-backlog \
  SDK=macosx26.5 LLVM="$LLVM" C_INSTALL="$C_INSTALL" APPLE_SDK="$APPLE_SDK" WORK="$WORK"
```

Use a fresh `WORK` directory. Read `header-backlog.json` and `header-review.md`.
A completed backlog with open findings exits nonzero. Check that the report
exists and inspect its `input_issues` before treating findings as current.
Read the two discovery traces separately for optional roots.

For the individual Python commands in the references, set the import path
from the repository root.

```sh
REVIEW=.agents/skills/review-macos-c-sdk
export PYTHONPATH="$PWD/$REVIEW/scripts${PYTHONPATH:+:$PYTHONPATH}"
```

1. Reproduce one affected public include or client on arm64.
   Record the target, deployment minimum, feature macros, compiler, source
   lock, and reference result.
2. Follow the installed manifest receipt to the owning recipe and pinned
   Apple OSS install rule. For a link failure, identify the exact Mach-O
   name and the library the client binds through. Attribute SDK Gen
   framework or stub defects to composition.
3. Ask Corentin as soon as you hit a source gap that requires a choice.
   Ask before using an unproven source, departing from an upstream rule,
   inferring ABI or availability, applying a workaround to get a test
   through, changing approved scope, or weakening a check. Include the
   reproducer, evidence, recommendation, and impact of leaving the gap
   open. Continue unrelated investigations.
4. Apply the approved change in the owning recipe or record the decision
   with its evidence and reopening condition. Rerun the affected cases
   and regenerate the reports. Keep unexplained findings open after a
   successful consumer build.

## Choose the relevant reference

- [Add or update an SDK source lock](source-locks.md) when changing pins.
- [Header workflows and approval ledgers](scripts/sdk_review/headers/README.md)
  for coverage, source-lock upgrades, and SDK Gen comparisons.
- [Interface and code generation diagnostics](scripts/sdk_review/headers/c_interface_review.md)
  for a changed declaration, layout, macro, or availability boundary.
- [Link diagnostics](scripts/sdk_review/linkage/diagnose_links.md) for a
  failing client. Use the [header-to-library workflow](scripts/sdk_review/linkage/sdk_header_linkage.md)
  for a broader provider investigation.
- [SDK Gen composition evidence](https://github.com/hermeticbuild/apple-sdk-gen/blob/main/docs/composition-gaps.md) for a framework or stub gap.
