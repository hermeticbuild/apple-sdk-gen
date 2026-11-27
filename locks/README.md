# Apple OSS source locks

Each SDK version has one JSON lock. The SDK version and reference build
identify the SDK used for comparison. The distribution tag and peeled
commit identify Apple's operating-system source snapshot.

- `projects` pins the sources for the standalone C installation and the minimal SDK.
- `full_projects` pins the additional sources for the full SDK, including
  objc4 and the Apple OSS framework sources. SDK 26.0 supports the C installation.

The 26.5 lock also records the official LLVM archive, the paths to extract,
and the DocC snapshot.

## Prepare and install

From the repository root:

```sh
SDK=macosx26.5
make prepare-c-sources prepare-llvm SDK="$SDK"
make install SDK="$SDK" OUT="$C_INSTALL"
make test SDK="$SDK" OUT="$C_INSTALL"
```

`make prepare-sources` prepares the C checkouts under
`build/inputs/sources/$SDK` and the additional full SDK checkouts under
`build/inputs/sources/$SDK-full`. Both use the Git cache in
`build/inputs/git`. Set `OFFLINE=1` to reuse local inputs.
The fetch command also accepts an explicit lock and destination. Add
`--full` to select the additional full SDK projects.

```sh
python3 -m tools.fetch_sources --lock "locks/$SDK.json" --dest "$SOURCE_ROOT"
```

Make verifies the source pins and rejects dirty checkouts. The C
installation copies the lock to `source-lock.json` and writes a
`header-manifest.tsv`. The internal `install-objc4` target stages the
Objective-C runtime headers and records the verified full source group.

Use the [SDK review skill](../.agents/skills/review-macos-c-sdk/SKILL.md)
when selecting or qualifying a new source lock.

The two macOS versions use the same Make recipes. The SDK identifier selects
the locked sources and scopes review data.
