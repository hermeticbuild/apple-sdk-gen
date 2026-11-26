# SystemConfiguration

Stage the 15 public headers and module map of the macOS
`SystemConfiguration.framework` target in the distribution's configd
gitlink. The patch narrows `SCPreferences.h`'s Security include to Apple's
public `Authorization.h`, which declares the only Security type used by
these headers. Preserve the APSL notices.

Run Clang InstallAPI over the staged public headers to emit the
`Versions/A/SystemConfiguration` stub for arm64 and x86_64.
Use Clang's system framework search path for the staged framework headers.
The recipe covers the public C declarations. The probe includes the
reachability header directly and the full umbrella separately, then links and runs
reachability and preferences clients.

The loaded macOS 26.5.2 SystemConfiguration image reports
`MH_APP_EXTENSION_SAFE` on both architectures. Pass that setting to
InstallAPI and require a warning-free application-extension link.

- [Apple header phase and build settings](https://github.com/apple-oss-distributions/configd/blob/f6245c30f907567887bd7b4e1639dc3f3edea4f7/configd.xcodeproj/project.pbxproj)
- [Apple's module map](https://github.com/apple-oss-distributions/configd/blob/f6245c30f907567887bd7b4e1639dc3f3edea4f7/SystemConfiguration.fproj/Modules/SystemConfiguration.modulemap)
