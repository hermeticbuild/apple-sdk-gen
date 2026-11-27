# macOS framework enum ABI

Apple documents the values of `NSTextAlignment.center` and `.right` as 1 and 2 on Apple silicon and iOS, and 2 and 1 on Intel macOS. Intel binaries retain the Intel values under Rosetta. This establishes the target ABI independently of a copy of the SDK. [Apple, center](https://developer.apple.com/documentation/appkit/nstextalignment/center) · [Apple, right](https://developer.apple.com/documentation/appkit/nstextalignment/right)

The pinned Apple OSS CarbonHeaders template predates Apple silicon. The public objc2 AppKit bindings identify the compatibility switch as `TARGET_ABI_USES_IOS_VALUES` and apply it to text alignment. This corroborates the spelling and its interpretation. We have no Apple OSS packaging rule or definition for this macro. [objc2 switch](https://github.com/madsmtm/objc2/blob/8a5abacd90d5403fc0463459a35826f892b9142e/framework-crates/objc2-app-kit/src/lib.rs) · [objc2 consumer](https://github.com/madsmtm/objc2/blob/8a5abacd90d5403fc0463459a35826f892b9142e/framework-crates/objc2-app-kit/src/text.rs)

The recipe derives a value of 1 for a macOS arm64 client and 0 for a macOS x86_64 client using Clang's target predefines. Other targets receive no definition from this derivation. The 26.5 SDK is used for differential tests only. [C fixture](../../.agents/skills/review-macos-c-sdk/scripts/sdk_review/headers/fixtures/c_interfaces/abi_target_value.c)

To verify the framework consumer, preload the generated header while compiling the reference AppKit header. Repeat on each architecture and repeat without the forced include for the reference control.

```sh
"$LLVM/bin/clang" --no-default-config -target "$ARCH-apple-macos11" -isysroot "$APPLE_SDK" \
  -include "$C_INSTALL/usr/include/TargetConditionals.h" -fblocks -fsyntax-only \
  .agents/skills/review-macos-c-sdk/scripts/sdk_review/headers/fixtures/appkit_text_alignment.m
```
