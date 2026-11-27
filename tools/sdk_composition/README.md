# Compose a macOS SDK

Use [the release build](../../release/README.md) for both archives.
`make compose-sdk` reads the selected lock, generated SDK, and prepared
sources.

The composer has two variants.

- `--variant minimal` installs the C headers, SIMD headers, and system linker
  stubs.
- `--variant full` adds libc++ and libc++abi headers and generated frameworks.
  Pass `--objc4-install` for the Objective-C runtime headers.

The full variant includes all generated frameworks by default. Repeat
`--framework NAME` for a subset. Use `--prepared-framework NAME DIRECTORY`
to supply a replacement bundle, or `--framework-overlay NAME DIRECTORY`
to replace files in a selected generated bundle. Use `--external-stub`
to include each separately produced linker stub and its aliases.

The composer compares the generated SDK version with `--lock`, verifies
the C and objc4 source pins, and records its inputs in `composition.json`.
The same tool handles both archives. See
[the release driver](../../release/build-composed-sdk.sh) for the exact
invocations.

## libiconv and libcharset

Generate the two separate libraries before composing the SDK. The producer
reads the pinned Git objects for Apple's libiconv-115.120.2, the standalone
C header installation, and the pinned macOS arm64 LLVM projection. macOS
`plutil` reads the Xcode project. The compiler uses a temporary sysroot
containing only C headers verified against the installation manifest.

```sh
python3 -m components.libiconv.generate_stubs \
  --source "$ICONV_SOURCE" --c-install "$C_INSTALL" --llvm "$LLVM" --out "$STUBS"
```

Both dylibs use the Release target's public and private header phases, product
names and versions. For libiconv the TAPI configuration supplies `-DIN_TAPI`,
the Citrus include path and the reexport of the freshly generated libcharset.
The install script specifies the two unversioned symlinks. The generated
`manifest.json` records the source revision, tool and C manifest digests,
registered headers and output digests.
[Project](https://github.com/apple-oss-distributions/libiconv/blob/7fb0198429570d3b6aa562d228a6ea5936d15c05/libiconv.xcodeproj/project.pbxproj)
· [TAPI configuration](https://github.com/apple-oss-distributions/libiconv/blob/7fb0198429570d3b6aa562d228a6ea5936d15c05/xcodeconfig/libiconv.xcconfig)
· [Install aliases](https://github.com/apple-oss-distributions/libiconv/blob/7fb0198429570d3b6aa562d228a6ea5936d15c05/xcodescripts/dest_cleanup.sh)

Append these four arguments to `compose_sdk`.

```sh
--external-stub "usr/lib/libiconv.2.tbd=$STUBS/usr/lib/libiconv.2.tbd" \
--external-stub "usr/lib/libiconv.tbd=$STUBS/usr/lib/libiconv.tbd" \
--external-stub "usr/lib/libcharset.1.tbd=$STUBS/usr/lib/libcharset.1.tbd" \
--external-stub "usr/lib/libcharset.tbd=$STUBS/usr/lib/libcharset.tbd"
```

For qualification, export `ICONV_SOURCE`, `C_INSTALL` and `LLVM` and run
`python3 -m unittest -v components.libiconv.test_stubs`. The tests
check reproducibility, link an arm64 client against `-liconv`, and inspect the
two-level bindings for `iconv_open` and `locale_charset`.

Setting `ICONV_REFERENCE_SDK` additionally compares the products with the macOS
26.5 SDK. All 95 direct iconv exports and both charset exports match, including
the reexport edge and dylib versions. The producer targets macOS arm64 with
a deployment floor of 11.0. The comparison uses the reference arm64e target.
Upstream LLVM emits `not_app_extension_safe` for
these project settings. App-extension compatibility remains unqualified.
