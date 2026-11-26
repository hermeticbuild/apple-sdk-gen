# CoreVideo pixel buffers

The local public surface covers pixel buffer creation, reference counts,
layout queries, and CPU locks. The declarations are rendered locally from
Apple's public CoreVideo API and use the `OSType` and CF pointer types
already supplied by the Apple OSS CoreFoundation recipe. The pixel formats
are the documented RGB bit depth and BGRA and YUV FourCC values.

- [Pixel buffer API and layout](https://developer.apple.com/documentation/corevideo/cvpixelbuffer?language=objc)
- [Pixel format constants](https://developer.apple.com/documentation/corevideo/pixel-format-identifiers?language=objc)
- [Release callback](https://developer.apple.com/documentation/corevideo/cvpixelbufferreleasebytescallback)

Clang InstallAPI generates the stub from the staged header. Its
versioned name is the installed CoreVideo image's name. The runtime
probe creates a BGRA buffer, checks its dimensions, row size and CPU
address, then unlocks and releases it.
