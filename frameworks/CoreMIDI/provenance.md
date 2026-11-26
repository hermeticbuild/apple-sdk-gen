# CoreMIDI

The local C header carries forward the handwritten macOS audio profile
from the SDK Gen prototype based on `0828b2e9`. It supplies the device
identifier types and two device discovery functions. The whole local
header differs from its Xcode 26.5 counterpart. The
[ABI probe](test.c) checks the identifier size and the
two signatures from [exports.list](exports.list).
[Device count documentation](https://developer.apple.com/documentation/coremidi/midigetnumberofdevices())
· [Device lookup documentation](https://developer.apple.com/documentation/coremidi/midigetdevice(_:))
