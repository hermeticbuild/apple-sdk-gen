# Scalar binary16 math on macOS

The 26.5 Libm recipe adds thirteen C declarations when the compiler
supports `_Float16` on macOS arm64 or x86_64. The return and argument
types come from the pinned LLVM libc functions of the same base name.
Darwin prefixes the C names with two underscores. The linker spellings
come from compiling the installed declarations with Clang.
[LLVM libc signatures](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/libc/include/math.yaml)

The availability check compares Apple's macOS 14.7 (23H124) and initial
15.0 (24A335) full OTA releases. Identify the OS builds from the OTA
metadata, reconstruct the system cryptex from the OTA member for each
architecture, mount read-only, locate `/usr/lib/system/libsystem_m.dylib`,
then query its Mach-O export trie for the thirteen candidate names. Use
`_ceil`, `_fma`, `_rint` and `_sqrt` as positive controls on each image.
Independent inspection of the current runtime supplies the 26.5.2 control.
[Apple 14.7 OTA](https://updates.cdn-apple.com/2024FallFCS/patches/062-78774/AC2D502C-ACE3-495C-8BF3-1ABEBFE7237A/com_apple_MobileAsset_MacSoftwareUpdate/c4f586faec1ab75e54765aec2f70846c4c6d1528.zip) · [Apple 15.0 OTA](https://updates.cdn-apple.com/2024FallFCS/patches/062-78498/22C3E101-2A4E-4B47-B5AC-7C8A2D7B85F1/com_apple_MobileAsset_MacSoftwareUpdate/7d763b0793c8e214f2d9bb078a0cba7b470e57e2.zip)

| Runtime cache | 14.7 / 23H124 libm UUID (0 of 13) | 15.0 / 24A335 libm UUID (13 of 13 strong) |
| --- | --- | --- |
| Apple Silicon arm64e | `39e9dc0c-ec48-34b8-9b19-9d87f51f4e63` | `a9f7fdc9-bc69-3406-bfc0-7278591fb060` |
| Rosetta x86_64 | `5e2516f7-0c28-34c5-bd5d-43bab390df63` | `63aac0f4-3b29-34d6-9ff1-1005868112fe` |
| Intel x86_64h | `eab4229a-72c0-3e27-8acc-2d8b0ed63ec0` | `6ab6bcc3-f24d-3299-a596-e5c28497aa08` |

For compile-only signature coverage, run `make test` with SDK 26.5.
For import and behavior checks, use the [runtime procedure](../../.agents/skills/review-macos-c-sdk/scripts/sdk_review/headers/half_math_runtime.md).
