# Apple OSS source locks

Each JSON file resolves the selected projects for one canonical SDK name.
Both current locks use the macOS header recipes. The SDK version and reference
SDK build describe qualification, while the distribution tag and peeled
commit identify Apple's operating-system source snapshot. Deployment targets
are chosen separately by the qualification commands.

## Prepare and install

From the repository root:

```sh
SDK=macosx26.5
python3 -m tools.sources.locked_sources prepare --sdk "$SDK"
make install SDK="$SDK" CLANG="$LLVM_CLANG" OUT="$C_INSTALL"
make test SDK="$SDK" CLANG="$LLVM_CLANG" OUT="$C_INSTALL"
```

Preparation fetches only the locked commits into a Git cache under
`build/source-cache` and checks them out in `build/sources/$SDK`. Pass
`--offline` to prepare from a populated cache without contacting a remote.
Pass `--cache` to share a cache across checkouts. For a different checkout
directory, pass the same absolute path as `--source-root` to preparation
and `SOURCE_ROOT` to Make.
Prepare into a new directory when replacing or refreshing a tree. Each
version can build independently from its own prepared tree.

Make checks that the source tree matches the lock and that the project
checkouts are clean. Installation itself requires no network. The output
includes `source-lock.json` beside `header-manifest.tsv`.

Run the cache and checkout tests with `python3 -m unittest discover -s tools/sources`.

The optional Objective-C layer has its own lock and checkout under
`build/sources/macosx26.5-objc4`. It never enters the standalone C installation.

```sh
python3 -m tools.sources.locked_sources prepare --sdk macosx26.5 --profile objc4
make install-objc4 SDK=macosx26.5 OUT="$OBJC4_INSTALL"
```

Use the [SDK review skill](../.agents/skills/review-macos-c-sdk/SKILL.md)
when selecting or qualifying a new source lock.

The two macOS versions use the same Make recipes. The SDK identifier selects
the locked sources and scopes review data.
