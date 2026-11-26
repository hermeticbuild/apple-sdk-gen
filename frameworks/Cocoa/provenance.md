# Cocoa

Generate the umbrella directly with the pinned Apple SDK Gen Cocoa recipe.
Apple documents Foundation, AppKit, and Core Data as its three header
imports. Inspection of the loaded macOS 26.5.2 Cocoa image on arm64 and
x86_64 confirms the AppKit and Core Data reexports and two version data
symbols. The linker stub refers to the flat names of the generated child
stubs. This matches the local framework layout while preserving Cocoa's
installed dylib identity.

The fixture links AppKit and Core Data calls through `-framework Cocoa`
and runs them on both architectures. Its coverage depends on the staged
Foundation, AppKit, and Core Data profiles.

- [Apple's Cocoa umbrella](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/OSX_Technology_Overview/CocoaApplicationLayer/CocoaApplicationLayer.html)
- [SDK Gen Cocoa recipe](https://github.com/apple-cross-toolchain/apple-sdk-gen/pull/11)
