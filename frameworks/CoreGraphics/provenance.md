# CoreGraphics geometry

The local recipe puts the documented `CGFloat`, `CGPoint`, `CGSize`,
and `CGRect` declarations in the public `CGGeometry.h` path. The
umbrella uses those declarations. The module map treats the geometry
header as textual so Foundation can alias the geometry records without
importing the graphics umbrella.

[Apple's geometry API](https://developer.apple.com/documentation/coregraphics/cggeometry)
· [Clang textual headers](https://clang.llvm.org/docs/Modules.html#header-declaration)

The fixture checks the layout and both include orders for arm64.
The Cocoa module fixture checks the local framework composition.

SDK Gen supplies the Objective-C++ fixes. It renders the documented
Boolean callbacks with `bool`, treats `CGBitmapInfo` as an unsigned
32-bit bitmask and initializes the two host byte-order and three font
index constants omitted by DocC. Apple's archived CGImage and CGFont
references identify the bit layout, native byte-order constants and
font sentinel values. The .NET bindings corroborate the newer masks.
Pinned Clang confirmed the same 17 constant values as Xcode 26.5 on
arm64. The composed Model I/O module fixture exercises the full
CoreGraphics import in Objective-C++20.

SDK Gen also uses C linkage for C APIs under Objective-C++. The
window-level key values follow Apple's archived public enumeration
and its current documentation. All 22 values matched Xcode 26.5
on arm64. OpenCV's Cocoa backend calls `CGWindowLevelForKey` through
that interface.

- [Apple CGImage Reference](https://leopard-adc.pepas.com/documentation/GraphicsImaging/Reference/CGImage/Reference/reference.html)
- [Apple CGFont Reference](https://leopard-adc.pepas.com/documentation/GraphicsImaging/Reference/CGFont/CGFont.pdf)
- [.NET CoreGraphics bindings](https://github.com/dotnet/macios/blob/36c7da52d3f0a7d66adca044040db5eb6231f5bd/src/CoreGraphics/CGImage.cs)
- [Apple Quartz Display Services Reference](https://leopard-adc.pepas.com/documentation/GraphicsImaging/Reference/Quartz_Services_Ref/Reference/reference.html)
