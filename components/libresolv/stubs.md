Run `make -f components/libresolv/stubs.mk` from the repository root with the 26.5 C tree and
the pinned source and LLVM inputs. The Apple project specifies
`__BIND_INSTALLAPI`, the extra public header `installapi.h`, and the
private header `dns_private.h` with three exported declarations. The
output provides `libresolv.9.tbd` and Apple's `libresolv.tbd` alias.

The macOS 15.4 header condition makes the legacy `_res` data a libSystem
dependency for earlier clients. Scan at that boundary so the resolver
stub only exports its own symbols. TBD v4 preserves compatibility
with earlier deployment targets.

The loaded macOS 26.5.2 resolver library reports `MH_APP_EXTENSION_SAFE`
on arm64 and x86_64. Pass that setting to InstallAPI and require a
warning-free application-extension link in the resolver probe.

- [Apple's InstallAPI flags](https://github.com/apple-oss-distributions/libresolv/blob/e48cd914edc1cb14f8289b8e2dfdaac360481cd2/xcodescripts/libresolv.xcconfig)
- [Public and private header phases](https://github.com/apple-oss-distributions/libresolv/blob/e48cd914edc1cb14f8289b8e2dfdaac360481cd2/libresolv.xcodeproj/project.pbxproj)
- [Alias rule](https://github.com/apple-oss-distributions/libresolv/blob/e48cd914edc1cb14f8289b8e2dfdaac360481cd2/xcodescripts/links.sh)
