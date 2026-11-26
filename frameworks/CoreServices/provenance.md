# CoreServices

This opt-in macOS profile supplies the LaunchServices APIs used by GLib's
content-type and application-info backends. It uses the existing Apple OSS
CoreFoundation recipe and the generated Apple OSS CarbonHeaders
`MacTypes.h` for its dependency types. The macOS 26.5 Apple OSS
distribution has no LaunchServices or CoreServices source project.
[macOS 26.5 source inventory](https://github.com/apple-oss-distributions/distribution-macOS/tree/83390100289cedfe669c31a96c94326d31afa1ed)
· [Pinned CarbonHeaders](https://github.com/apple-oss-distributions/CarbonHeaders/blob/214a9ae7ab3c0c78ddb50328ca226e6313c4c782/MacTypes.h)

`LaunchServices/UTType.h` derives its function and constant declarations
from Apple's legacy C API references. The machine-readable CoreServices
DocC index lists the functions and omits all six legacy data constants
needed by GLib. The archived UTI guide and its linked constants table
identify the data declarations independently.
[CoreServices DocC index](https://developer.apple.com/tutorials/data/index/coreservices)
· [Apple UTI guide](https://developer.apple.com/library/archive/documentation/FileManagement/Conceptual/understanding_utis/understand_utis.tasks/understand_utis_tasks.html)
· [Apple system-declared UTIs](https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/UTIRef/Articles/System-DeclaredUniformTypeIdentifiers.html)

`LaunchServices/LaunchServices.h` derives the C functions and
`LSLaunchURLSpec` field order from Apple's API descriptions. The
`core-services` Rust binding corroborates the two-byte record packing and
the launch default value. The adjacent ApplicationServices fixture
compares the layout with Xcode 26.5 on both architectures.
[Launch Services API](https://developer.apple.com/documentation/coreservices/launch_services?language=objc)
· [Documented record initializer](https://developer.apple.com/documentation/coreservices/lslaunchurlspec/1446360-init)
· [Documented roles value](https://developer.apple.com/documentation/coreservices/lsrolesmask/klsrolesall)
· [Rust ABI corroboration](https://docs.rs/core-services/1.0.0/src/core_services/launch_services.rs.html)

Clang InstallAPI emits the LaunchServices child stub from the profile
headers. Runtime symbol lookup on macOS 26.5.2 finds all 17 symbols in
the versioned LaunchServices image in both slices. Apple's runtime
CoreServices umbrella reexports that image. The recipe emits that
observed relationship. Xcode 26.5 is used for comparison only.

For a bulk SDK composition, pass `CORE_SERVICES_TBD` from the pinned SDK
Gen artifact to preserve its generated linker exports in the umbrella,
including FSEvents. The recipe normalizes the generated install name to
the versioned name observed above before merging with LLVM. The prepared
umbrella header exposes the qualified LaunchServices subset. The
unmodified generated stub remains an input with its original coverage
limits.

The other CoreServices subframeworks and the rest of LaunchServices remain
open, including direct includes of the original `UTCoreTypes.h` and
`LSOpen.h` headers. The separate CLI diagnostic already verified selected
FSEvents stub entries.
