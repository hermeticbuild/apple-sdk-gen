# CoreFoundation

When Foundation is staged, add a relative alias at
`Versions/A/CoreFoundation.tbd` for its recorded runtime reexport. The alias
resolves to the same InstallAPI output used by ordinary framework links.

Generate application-extension-safe linker metadata. The loaded macOS 26.5.2
CoreFoundation image reports `MH_APP_EXTENSION_SAFE` on arm64 and x86_64.
The probe links in application-extension mode with linker warnings fatal.

Stage the 40 paths in [headers.list](headers.list) from the pinned
Apple OSS CF Git objects. The list carries forward the qualified mapping
in `a717b3ba89aff56cc5b202cbab4df33bad8a0586:inputs/header-sources.tsv`.
The selected files carry Apple Public Source License notices. Preserve
the notices and use the pinned project's license for the distribution
inventory.
[Pinned CF source](https://github.com/apple-oss-distributions/CF/tree/dc54c6bb1c1e5e0b9486c1d26dd5bef110b20bf3)
· [Project license](https://github.com/apple-oss-distributions/CF/blob/dc54c6bb1c1e5e0b9486c1d26dd5bef110b20bf3/APPLE_LICENSE)

[modern-c-api.patch](modern-c-api.patch) brings in the nullability and C
API used by newer clients from pinned Swift Corelibs Foundation. The patch
adds `CFErrorDomain`, the assume-nonnull macros, and one-argument `CF_ENUM`.
Its source and license are recorded with the patch.

[modern-framework-macros.patch](modern-framework-macros.patch) uses the
same Swift Corelibs Foundation source for public availability and Swift
importer macros required by Apple's Security headers. The macOS branch
accepts underscore-version attributes on Clang versions that support
them, including deprecation messages. It also declares the closed enum
used by Secure Transport with Clang's enum extensibility attribute.

Clang InstallAPI reads the staged public headers and
[installapi.h](installapi.h), which declares the compiler's 64-bit
`CFSTR` reference from Apple's pinned `CFRuntime.c`. The two-architecture
stub includes `CFRetain` and `CFRelease` from the public headers. The
[link probe](test.c) exercises both calls, a constant string, a typed
error domain, and the compatibility macros.
