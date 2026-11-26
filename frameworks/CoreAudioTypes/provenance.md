# CoreAudioTypes

The local C header carries forward the handwritten macOS audio profile
from the SDK Gen prototype based on `0828b2e9`. Apple documents the
`AudioStreamBasicDescription` fields and their order. The
[ABI probe](test.c) checks its size and field offsets on
both targets. The whole local header differs from its Xcode 26.5
counterpart. The stub exports no symbols.
[Stream description documentation](https://developer.apple.com/documentation/coreaudiotypes/audiostreambasicdescription)
