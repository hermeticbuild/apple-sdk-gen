# Security

Stage Apple's public `Security.h` and its 76-header Security include
closure from the matching 26.5 Security gitlink. The compiler reached
the same [paths](headers.list) on arm64 and x86_64 with Objective-C ARC
and blocks. `Authorization.h` continues to supply `AuthorizationRef`
for SystemConfiguration. The staged `SecCode.h` patch selects the
WebKit-derived type from the standalone C installation when a full XPC
header is absent. The libDER dependencies also come from the C installation.

Compose this recipe as a path overlay on SDK Gen Security. SDK Gen
supplies the linker stub. The [consumer probe](../../tests/composed_sdk/security.m)
links and calls `SecCopyErrorMessageString` on both architectures.

- [Security source and notices](https://github.com/apple-oss-distributions/Security/blob/97c3a4296c1ea06b0fe1877a7e616aa84450b5b2/OSX/libsecurity_authorization/lib/Authorization.h)
- [Security umbrella](https://github.com/apple-oss-distributions/Security/blob/97c3a4296c1ea06b0fe1877a7e616aa84450b5b2/base/Security.h)
- [macOS 26.5 OSS distribution](https://github.com/apple-oss-distributions/distribution-macOS/tree/83390100289cedfe669c31a96c94326d31afa1ed)
