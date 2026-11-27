# Look up Mach-O symbols in the local reference SDK

Pass exact Mach-O spellings, including any leading underscores or dollar
suffixes. Use repeated `--symbol` arguments for a short list or `--symbols-file`
for a bulk join, with one spelling per line. Use `--raw-symbol` for a separate
literal source-token check of a few names. Keep the report local.

```sh
python3 -m sdk_review.linkage.lookup_tbd_symbols \
  --sdk "$SDK" --llvm "$LLVM" --symbols-file "$MACH_O_NAMES" \
  --raw-symbol _add_profil --raw-symbol _profil --raw-symbol _unwhiteout \
  --out /tmp/sdk-tbd-symbols.json
```

The scanner visits physical `.tbd` paths under the SDK, including nested and
private framework directories. It resolves in-SDK TBD aliases and records
directory aliases. A dangling link, escape, unreadable file, or unsupported
TBD sets `complete` to false and exits 2 after writing the issues and any
partial results. Use only complete reports for absence conclusions.

`llvm-readtapi` validates each physical source and its embedded documents. The
scanner verifies that conversion preserves each document's install name and
declared targets. For v4, it reads symbol roles and target groups from the
original document. A v5 conversion can merge roles for a symbol directly
exported on one target and explicitly reexported on another.

The JSON `matches` array contains flat rows with `symbol`, `path`, `document`,
`install_name`, `targets`, `role`, `segment`, and `kind`. `document` is the
one-based document index in the physical file. `segment` is null for v4.
Roles identify direct exports, explicit symbol reexports, and undefined rows.
Objective-C class entries supply both class and metaclass spellings. Target
names are the exact SDK spellings, including `arm64e-macos` where applicable.
`reexport_edges` records incoming whole-library reexport edges on the same
target spellings. `linker_directives` records explicit policy mentions.
`raw_candidates` and `raw_directive_candidates` report literal source tokens
for requested names. Raw checks concern textual spellings, including directive
payloads, and therefore do not expand Objective-C class encodings.

## SDK 26.5 check

The scan covered 3,259 physical paths, 3,520 primary and embedded documents,
2,839 TBD aliases, and 3,524 directory aliases with no issues. `_add_profil`,
`_profil`, and `_unwhiteout` have no matching rows, directive mentions, or raw
token candidates. `___fpclassify` appears in `libsystem_m` on Intel macOS
targets in the two embedded umbrella variants and the standalone component.

Positive controls find `_iconv_open`, `_zlibVersion`, `_initscr`,
`_sqlite3_open`, `_res_9_query`, and `_xmlReadMemory` in separate libraries.
`_compression_encode_buffer` appears in both `libcompression` and the nested
private `BootabilityBrain` framework. `libc.tbd`, `libm.tbd`, `libpthread.tbd`,
and `libSystem.tbd` resolve to `usr/lib/libSystem.B.tbd`. `libiconv.tbd`,
`libz.tbd`, and `libcurses.tbd` resolve to versioned stubs outside the umbrella.

A 20,000-name query completed in 47 seconds with eight workers on the
qualification host. Run the fixture tests with
`LIBSYSTEM_TEST_LLVM="$LLVM" python3 -m unittest sdk_review.linkage.test_lookup_tbd_symbols`.
