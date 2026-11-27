# AppKit

The four pasteboard constants used by Codex are documented `NSString` data
exports and already ship in SDK Gen 0.0.7. Declaring them in the local
umbrella lets InstallAPI preserve them in the versioned AppKit stub.
[Apple pasteboard types](https://developer.apple.com/documentation/appkit/nspasteboard/pasteboardtype?language=objc)
· [Apple pasteboard reading options](https://developer.apple.com/documentation/appkit/nspasteboard/readingoptionkey)

The local profile exposes the documented NSColor sRGB constructor and
component properties, plus the common NSResponder, NSApplication, NSView,
and NSWindow class declarations and the window title property. It gets
NSObject through the Foundation layer's pinned Apple OSS objc4 headers.
The scalar ABI follows Apple's LP64 CGFloat documentation.

Clang InstallAPI emits the arm64 Objective-C class exports from the staged
headers. The installed AppKit image on macOS 26.5.2 (25F84) uses the
`Versions/C/AppKit` install name and reexports versioned Foundation. The recipe
passes the staged Foundation stub to InstallAPI to describe that edge and
provides both flat and versioned lookup paths. The Cocoa probe checks a
color and the responder hierarchy without opening a window.

```sh
dyld_info -dependents /System/Library/Frameworks/AppKit.framework/Versions/C/AppKit
```

- [NSColor class and components](https://developer.apple.com/documentation/appkit/nscolor?language=objc)
- [sRGB constructor](https://developer.apple.com/documentation/appkit/color-creation?language=objc)
- [CGFloat on 64-bit systems](https://developer.apple.com/documentation/corefoundation/cgfloat-swift.struct)
- [AppKit class catalog](https://developer.apple.com/documentation/appkit?language=objc)
## Windowing and controls

The windowing declarations follow the public AppKit Objective-C interfaces.
The GNUstep headers corroborate the window styles, event values,
autoresizing options and line-breaking constants. Foundation supplies the
LP64 geometry aliases. AppKit's status window level uses the corresponding
CoreGraphics key to look up the level at runtime.

- [NSWindow](https://developer.apple.com/documentation/appkit/nswindow?language=objc)
- [NSWindow levels](https://developer.apple.com/documentation/appkit/nswindow/level-swift.struct)
- [NSView](https://developer.apple.com/documentation/appkit/nsview?language=objc)
- [NSBitmapImageRep](https://developer.apple.com/documentation/appkit/nsbitmapimagerep?language=objc)
- [GNUstep AppKit interfaces and values](https://github.com/gnustep/libs-gui/tree/af9ee9812aaef80a00645b3dcea29ab4d0eef8d8/Headers/AppKit)

The Cocoa fixture checks the collection and image APIs by calling them
on macOS. The OpenCV Cocoa backend exercises the rest of the selected
windowing, image and control declarations in Objective-C++.

## Menu bar exports and alerts

The public AppKit DocC declarations provide the types for `NSBeep`,
`NSFontWeightSemibold`, both rectangle fill functions, the workspace
notification, and the four light and dark appearance names. The pinned
snapshot's generated AppKit stub exports all nine names. The arm64
macOS 26.5.2 AppKit image corroborates all nine. Declaring them in this
umbrella lets InstallAPI retain them with the recipe's versioned install
name and reexports. The C link fixture reproduces all nine unresolved
symbols from 0.0.8.

The `NSAlert` declarations cover creating and configuring an alert.
Apple's public interface gives the selectors and types. The pinned
GNUstep interface corroborates the three alert style values.

- [NSBeep](https://developer.apple.com/documentation/appkit/nsbeep())
- [Font weights](https://developer.apple.com/documentation/appkit/nsfont/weight)
- [Rectangle fills](https://developer.apple.com/documentation/appkit/nsrectfill)
- [Workspace accessibility notification](https://developer.apple.com/documentation/appkit/nsworkspace/accessibilitydisplayshoulddifferentiatewithoutcolor?language=objc)
- [System appearance names](https://developer.apple.com/documentation/appkit/nsappearance/name-swift.struct/accessibilityhighcontrastdarkaqua?language=objc)
- [NSAlert](https://developer.apple.com/documentation/appkit/nsalert)
- [GNUstep NSAlert.h](https://github.com/gnustep/libs-gui/blob/af9ee9812aaef80a00645b3dcea29ab4d0eef8d8/Headers/AppKit/NSAlert.h)

## NSImage

The AppKit recipe takes the `NSImage` interface from the umbrella generated
from the pinned macOS DocC snapshot. It stages that interface as
`AppKit/NSImage.h` and includes it from `AppKit/AppKit.h`. InstallAPI
lists both as public headers so the stub retains the `NSImage` class. The local
preamble supplies the pointer and option types needed by the generated
declarations. Foundation supplies the edge inset layout.
The DocC renderer exposes the documented `isTemplate` and `setTemplate:`
accessors in Objective-C++, where `template` is a keyword. Objective-C
also gets the property syntax.

DocC lists cache and TIFF compression case names without their numeric
values. The generated enum fallback assigns values by topic order.
The recipe uses the values corroborated by pinned GNUstep headers.
Apple documents the integer backing types. Microsoft's public macOS
bindings corroborate the two resizing values. The runtime fixture
checks a system symbol, property access, and the edge inset layout by value.

- [NSImage declarations](https://developer.apple.com/documentation/appkit/nsimage?language=objc)
- [CGImageRef](https://developer.apple.com/documentation/coregraphics/cgimage?language=objc)
- [NSEdgeInsets](https://developer.apple.com/documentation/foundation/nsedgeinsets?language=objc)
- [NSImageCacheMode](https://developer.apple.com/documentation/appkit/nsimage/cachemode-swift.enum?language=objc)
- [GNUstep cache values](https://github.com/gnustep/libs-gui/blob/af9ee9812aaef80a00645b3dcea29ab4d0eef8d8/Headers/AppKit/NSImage.h#L79-L84)
- [GNUstep TIFF compression values](https://github.com/gnustep/libs-gui/blob/af9ee9812aaef80a00645b3dcea29ab4d0eef8d8/Headers/AppKit/NSBitmapImageRep.h#L56-L65)
- [NSImageResizingMode](https://developer.apple.com/documentation/appkit/nsimage/resizingmode-swift.enum?language=objc)
- [.NET resizing values](https://learn.microsoft.com/en-us/dotnet/api/appkit.nsimageresizingmode?view=net-macos-26.5-10.0)
