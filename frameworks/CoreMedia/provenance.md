# CoreMedia timing and sample buffers

Apple's public CoreMedia declarations establish the timestamp and range
field order, widths, and function signatures. The sample buffer's image
buffer result uses the local CoreVideo public type.

- [CMTime fields and operations](https://developer.apple.com/documentation/coremedia/cmtime?language=objc)
- [CMTimeRange fields and operations](https://developer.apple.com/documentation/coremedia/cmtimerange?language=objc)
- [CMSampleBuffer](https://developer.apple.com/documentation/coremedia/cmsamplebuffer?language=objc)
- [Video format dimensions](https://developer.apple.com/documentation/coremedia/cmvideoformatdescriptiongetdimensions(_:))

Clang InstallAPI generates the stub at the installed CoreMedia image's
versioned name. The runtime probe passes a timestamp and a range by
value and checks the returned fields.
