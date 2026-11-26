# OpenAL

Copy `al.h` and `alc.h` verbatim from Apple's OpenAL-71 public header
selection. These files also match the Xcode 26.5 headers byte for byte.
The recipe reads them from the pinned Apple OSS Git objects.
[Apple OSS source](https://github.com/apple-oss-distributions/OpenAL/tree/f6f9a3c01868d07937a46425fe0ce555e3341bb2)

[exports.awk](exports.awk) extracts the declarations marked with
`AL_API`/`AL_APIENTRY` and `ALC_API`/`ALC_APIENTRY`. The 93
names reproduce the existing profile stub. The
[ABI probe](test.c) compiles both public includes and links a typed reference
to one function from each. The stub's symbols are inferred from the declarations.
