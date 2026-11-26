# AudioToolbox

The local C header carries forward the handwritten macOS audio profile
from the SDK Gen prototype based on `0828b2e9`. The profile records
Apple's documentation for the Audio Component descriptor and functions
as declaration and layout evidence. The whole header differs from its
Xcode 26.5 counterpart. That comparison does not establish the original
source of each line in the local draft.
[Descriptor documentation](https://developer.apple.com/documentation/audiotoolbox/audiocomponentdescription)
· [Component function documentation](https://developer.apple.com/documentation/audiotoolbox/audiocomponentcount(_:))

The five entries in [exports.list](exports.list) come from the local
profile and have typed references in the [ABI probe](test.c).
The `rules_rs` CoreAudio test also exercises enumeration through
`AudioComponentCount`.
