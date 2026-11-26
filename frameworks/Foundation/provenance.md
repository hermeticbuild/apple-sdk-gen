# Foundation

The trial exposes selected Objective-C string, collection, data, error, URL,
number, and date APIs. It uses `NSObject.h` and `objc.h` from the pinned Apple
OSS objc4 installation and `CFBase.h` from the CoreFoundation recipe.

The remaining declarations are local renderings of public declarations and
ABI facts. Apple documents the LP64 integer widths, both `NSRange` fields,
and the Objective-C collection methods. The runtime probe checks range
layout and by-value returns as well as behavior for the supported classes.
Other Foundation features require additional declarations and probes.

The Foundation enum, option, and nullability macros delegate to the
corresponding definitions in the staged Apple OSS CoreFoundation headers.
The composed SDK probe uses an `NS_ENUM` type and a declaration inside a
nonnull region on arm64.
[Apple OSS enum macros](https://github.com/apple-oss-distributions/CF/blob/dc54c6bb1c1e5e0b9486c1d26dd5bef110b20bf3/CFAvailability.h#L195-L215)

- [Apple OSS objc4](https://github.com/apple-oss-distributions/objc4)
- [LP64 Foundation scalar types](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/64bitPorting/HighLevelAPIs/HighLevelAPIs.html)
- [Range fields](https://developer.apple.com/documentation/xcode/reading-an-exception-message)
- [Range construction](https://developer.apple.com/documentation/foundation/nsmakerange(_:_:)?language=objc)
- [Object and collection declarations](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ProgrammingWithObjectiveC/FoundationTypesandCollections/FoundationTypesandCollections.html)
- [Foundation DocC catalog](https://developer.apple.com/documentation/foundation?language=objc)

The recipe accepts the pinned arm64 SDK Gen 26.5 Foundation stub and
the earlier SDK Gen 0.0.4 input. The macOS
26.5.2 (25F84) Foundation dylib has the `Versions/C/Foundation` install
name and reexports CoreFoundation. The 26.5 input already has the
versioned name. CoreFoundation owns Clang's
Objective-C constant string symbol. The staged patch adds that reexport to
the pinned SDK Gen input. The Foundation and CoreFoundation recipes provide
the versioned paths the linker resolves. Xcode 26.5 is a validation reference.

```sh
dyld_info -dependents /System/Library/Frameworks/Foundation.framework/Versions/C/Foundation
```

The local voice Foundation layer includes `VoiceFoundation.h` from its
umbrella. Apply [voice-modulemap.patch](voice-modulemap.patch) to that
prepared bundle before composition. The textual entry follows the existing
`NSPathUtilities.h` entry. It gives the voice declarations access to types
defined in the umbrella. The C++20 `test-Foundation-modules` target
reproduces the missing `NSUInteger` diagnostic without the patch and
compiles, links and runs with it.

```sh
patch -s -f -F 0 -V none -p1 -d "$VOICE_FOUNDATION_FRAMEWORK" \
  < frameworks/Foundation/voice-modulemap.patch
patch -s -f -F 0 -V none -p1 -d "$VOICE_FOUNDATION_FRAMEWORK" \
  < frameworks/Foundation/voice-array-generics.patch
```

The second patch gives the voice layer's mutable array an invariant
element parameter and passes that parameter to its `NSArray` superclass.
The composed `test-modelio` probe checks the type of
`mesh.submeshes.firstObject` through both classes.
[Apple's MDLMesh property declaration](https://developer.apple.com/documentation/modelio/mdlmesh/submeshes?language=objc)

The current Foundation recipe carries the same voice declarations and
adds the string, collection, thread, and run loop APIs used by OpenCV.
The LP64 geometry names alias the CoreGraphics records. The Cocoa and
Model I/O tests exercise collections and geometry without opening a window.

- [Apple NSFastEnumerationState](https://developer.apple.com/documentation/foundation/nsfastenumerationstate)
- [Apple NSGeometry types](https://developer.apple.com/documentation/foundation/nsrect)
- [Apple NSRunLoop](https://developer.apple.com/documentation/foundation/runloop?language=objc)
- [Apple NSUserNotification](https://developer.apple.com/documentation/foundation/nsusernotification?language=objc)

GLib's `gosxutils.m` imports the Foundation umbrella for its path lookup.
The staged `NSPathUtilities.h` restores the seven directory values, the
user-domain mask, and the function declaration used by that client. The
existing SDK Gen Foundation stub supplies the function export. The recipe
test calls it for the unexpanded Desktop path.
[Apple directory search documentation](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/LowLevelFileMgmt/Articles/StandardDirectories.html)
· [Pinned Swift Foundation values](https://github.com/swiftlang/swift-foundation/blob/511394753aa873fd390674301594b4bb8460a74b/Sources/FoundationEssentials/FileManager/SwiftFileManager.swift#L170-L215)
