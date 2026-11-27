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
make prepare-c-sources prepare-llvm SDK="$SDK"
make install SDK="$SDK" OUT="$C_INSTALL"
make test SDK="$SDK" OUT="$C_INSTALL"
```

`make prepare-sources` also prepares the objc4 and framework checkouts for
the full 26.5 SDK. The Git cache lives under `build/inputs/git` and the
checkouts under `build/inputs/sources`. Set `OFFLINE=1` to reuse local inputs.
The fetch command accepts an explicit lock and destination for other layouts:

```sh
python3 -m tools.fetch_sources --lock "locks/$SDK.json" --dest "$SOURCE_ROOT"
```

Make verifies the source lock and rejects dirty checkouts. Installation
writes `source-lock.json` and `header-manifest.tsv`. The separate
`make install-objc4` target builds the Objective-C runtime header layer.

Use the [SDK review skill](../.agents/skills/review-macos-c-sdk/SKILL.md)
when selecting or qualifying a new source lock.

The two macOS versions use the same Make recipes. The SDK identifier selects
the locked sources and scopes review data.
