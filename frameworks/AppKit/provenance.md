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
