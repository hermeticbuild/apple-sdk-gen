## LLVM proof composition

The reference Apple SDK Gen project's [README](https://github.com/apple-cross-toolchain/apple-sdk-gen/blob/main/README.md)
says its libSystem, libobjc, and libc++ stub symbol lists are refreshed from
an installed Xcode by
[`extract-darwin-libs.py`](https://github.com/apple-cross-toolchain/apple-sdk-gen/blob/main/tools/extract-darwin-libs.py).
The [framework recipes](../frameworks/README.md) record each replacement's
Apple OSS and local declaration inputs. CoreFoundation combines pinned APSL
headers with a compatibility backport from Swift Corelibs Foundation
under Apache-2.0 with the Runtime Library Exception. Its stub comes from
those headers and an Apple OSS runtime declaration. The generator's code
license does not by itself establish rights to
redistribute its Xcode-derived export data or documentation-derived content.

Apple's [Xcode and Apple SDKs Agreement](https://www.apple.com/legal/sla/docs/xcode.pdf)
limits Apple Software use to Apple-branded macOS hardware and restricts
separate SDK use and redistribution, while acknowledging rights that may be
conferred by open-source component licenses. Apple's
[Website Terms](https://www.apple.com/legal/internet-services/terms/site.html)
restrict copying and automated acquisition of site content. How those terms
apply to generated symbol facts and API declarations needs qualified review.
Do not treat the local composed SDK archive as cleared for public distribution
or non-Apple hardware use on the basis of this prototype.
