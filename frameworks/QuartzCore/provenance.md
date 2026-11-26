# QuartzCore layer contents

AppKit's `NSView.layer` returns the documented `CALayer`. The local
QuartzCore header exposes its public factory and object-valued
`contents` property for Objective-C and Objective-C++ callers.
Clang InstallAPI generates the class entry with the installed
QuartzCore image's `Versions/A/QuartzCore` install name.

- [AppKit's NSView.layer](https://developer.apple.com/documentation/appkit/nsview/layer)
- [QuartzCore's CALayer](https://developer.apple.com/documentation/quartzcore/calayer?language=objc)
- [CALayer.contents](https://developer.apple.com/documentation/quartzcore/calayer/contents)

The runtime probe creates a layer and calls both content accessors.
