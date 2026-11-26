# AudioUnit

The local C header carries forward the handwritten macOS audio profile
from the SDK Gen prototype based on `0828b2e9`. It uses
`AudioComponentInstance` from the sibling AudioToolbox recipe and declares
the initialization and uninitialization calls. The released SDK Gen
stub published just `_AudioUnit_stub`. The two real functions are in
[exports.list](exports.list) and have typed references in the
[ABI probe](test.c). The whole local header differs from
its Xcode 26.5 counterpart.
[Initialize documentation](https://developer.apple.com/documentation/audiotoolbox/audiounitinitialize(_:))
· [Uninitialize documentation](https://developer.apple.com/documentation/audiotoolbox/audiounituninitialize(_:))

In the HermeticBuild macOS 26.5 preview, the generator discovers these
declarations under AudioToolbox. The arm64 fixture nevertheless links
with `-framework AudioUnit` against Xcode 26.5 and records both imports
from AudioUnit. On macOS 26.5.2, `dyld_info -exports` shows both AudioUnit
exports forwarding to AudioToolbox. The composition uses this recipe's
AudioUnit stub and retains the generated AudioToolbox export table.
