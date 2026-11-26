# CoreAudio

The two local C headers carry forward the handwritten macOS audio profile
from the SDK Gen prototype based on `0828b2e9`. The profile uses Apple
documentation for the property types and signatures. It uses the
NullAudio driver's positional initializer and callback definitions to
establish driver vtable order and signatures. Apple's public
`CFPlugInCOM.h` supplies the initial COM slots via `IUNKNOWN_C_GUTS`.
The whole local headers differ from their Xcode 26.5 counterparts.
That comparison does not establish the original source of every line.
[Property address documentation](https://developer.apple.com/documentation/coreaudio/audioobjectpropertyaddress)
· [NullAudio driver sample](https://developer.apple.com/documentation/coreaudio/creating-an-audio-server-driver-plug-in)
· [Apple OSS COM header](https://github.com/apple-oss-distributions/CF/blob/dc54c6bb1c1e5e0b9486c1d26dd5bef110b20bf3/CFPlugInCOM.h)

The [ABI probe](test.c) checks all 23 driver slot offsets,
the property structure layout, and the two signatures in
[exports.list](exports.list). CoreAudioTypes and CoreFoundation supply
the types included by these headers.
