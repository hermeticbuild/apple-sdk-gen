# IOKit audio types

Copy `IOAudioTypes.h` verbatim from Apple OSS IOAudioFamily-740.1 to
`Headers/audio/IOAudioTypes.h`. The pinned source file carries an Apple
Public Source License notice. Preserve it and use the pinned project's
license for the distribution inventory.
[Source header](https://github.com/apple-oss-distributions/IOAudioFamily/blob/6fdf514055a9868fe20e4dc3845b78dfa5e27110/IOAudioTypes.h)
· [Project license](https://github.com/apple-oss-distributions/IOAudioFamily/blob/6fdf514055a9868fe20e4dc3845b78dfa5e27110/APPLE_LICENSE)

The [ABI probe](test.c) checks record sizes and field offsets for the audio
types. The stub also preserves the two power assertion exports used by
Codex. SDK Gen 0.0.7 includes both. Apple's pinned IOKitUser publishes their
declarations and implementations.
[IOPMLib.h](https://github.com/apple-oss-distributions/IOKitUser/blob/23a611d9d194b63465f6df2abfdda63d71c87e97/pwr_mgt.subproj/IOPMLib.h)
· [IOPMAssertions.c](https://github.com/apple-oss-distributions/IOKitUser/blob/23a611d9d194b63465f6df2abfdda63d71c87e97/pwr_mgt.subproj/IOPMAssertions.c)
