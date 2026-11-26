# AVFoundation capture, reading, and writing

The local declarations follow the C-family DocC data for the public
capture device, session, sample buffer delegate, asset reader and asset
writer interfaces. CoreMedia supplies the by-value timestamps and
CoreVideo supplies the image buffer handles.

- [Capture setup](https://developer.apple.com/documentation/avfoundation/capture-setup)
- [Capture device and frame rates](https://developer.apple.com/documentation/avfoundation/avcapturedevice?language=objc)
- [Sample buffer delegate](https://developer.apple.com/documentation/avfoundation/avcapturevideodataoutputsamplebufferdelegate?language=objc)
- [Asset reading](https://developer.apple.com/documentation/avfoundation/avassetreader?language=objc)
- [Asset writing](https://developer.apple.com/documentation/avfoundation/avassetwriter?language=objc)
- [Pixel buffer adapter](https://developer.apple.com/documentation/avfoundation/avassetwriterinputpixelbufferadaptor?language=objc)

Clang InstallAPI emits the client-facing entries under AVFoundation's
versioned public install name. The installed image resolves those entries
through its AVFCore and AVFCapture reexports. The test creates a capture
session and writer input on arm64 without accessing a camera.
