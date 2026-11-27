# Apple OSS sources for missing macOS 26.5 C headers

The official comparison SDK is build 25F70. Apple’s source distribution is
[`macos-265`](https://github.com/apple-oss-distributions/distribution-macOS/tree/83390100289cedfe669c31a96c94326d31afa1ed).
The standalone installation copies the public Libnotify and removefile headers
and the three reviewed libplatform headers directly from the matching Apple
source pins for SDKs 26.0 and 26.5. The copies preserve the source notices.

## Public Apple install rules

| Header | Pinned source and install evidence | Comparison |
| --- | --- | --- |
| `notify.h`, `notify_keys.h` | Libnotify at `227c145bcf26ec93e18304ba81306a3014d9bd56`. Both are Public in the Xcode header phase. `xcodeconfig/libnotify.xcconfig` sets `/usr/include`. [Project](https://github.com/apple-oss-distributions/Libnotify/blob/227c145bcf26ec93e18304ba81306a3014d9bd56/Libnotify.xcodeproj/project.pbxproj) | Both source headers match 25F70 byte for byte. |
| `removefile.h`, `checkint.h` | removefile at `ff74f69107ce34faea8a8cfd831debd7de5f759d`. Both are Public in the Xcode header phase. `xcodescripts/removefile.xcconfig` sets `/usr/include`. [Project](https://github.com/apple-oss-distributions/removefile/blob/ff74f69107ce34faea8a8cfd831debd7de5f759d/removefile.xcodeproj/project.pbxproj) | Both source headers match 25F70 byte for byte. |
| 15 `rpcsvc/*.h` paths | Librpcsvc at `395207bb8ae130fa6a859bac39c3c45912aac3d8`. Apple’s script runs `rpcgen -h` on each checked-in `.x` and installs the result to `/usr/include/rpcsvc`. [Install script](https://github.com/apple-oss-distributions/Librpcsvc/blob/395207bb8ae130fa6a859bac39c3c45912aac3d8/xcodescripts/install_rpcsvc.sh) | All 15 generated headers match 25F70 byte for byte using the host’s Xcode 26.5 `rpcgen`. The two installed YP headers remain Libinfo’s responsibility. |

The standalone profile omits these 15 generated RPC service headers. The
discovery probe still covers them. This command reproduces the headers and
stages their `.x` inputs for future use.

```sh
mkdir -p "$RPC_OBJ"
SRCROOT="$LIBRPCSVC" OBJROOT="$RPC_OBJ" DSTROOT="$RPC_DST" \
  /bin/sh "$LIBRPCSVC/xcodescripts/install_rpcsvc.sh"
```

## Other priority paths

| Header | Source and remaining work |
| --- | --- |
| `timingsafe.h` | The [pinned libplatform header](https://github.com/apple-oss-distributions/libplatform/blob/b7ed7cf5cf7dd12b98672435db2225a860f199d8/include/timingsafe.h) is byte-identical to 25F70. The earlier source-plus-SDK-path approval applies. |
| `string_x86.h` | The [pinned libplatform header](https://github.com/apple-oss-distributions/libplatform/blob/b7ed7cf5cf7dd12b98672435db2225a860f199d8/include/string_x86.h) contains the Intel declarations. 25F70 spells their availability as macOS 11.0 where the source says 10.16. The Intel probe pre-includes `string.h` for `size_t` and `__BEGIN_DECLS`. |
| `os/security_config.h` | The [pinned libplatform header](https://github.com/apple-oss-distributions/libplatform/blob/b7ed7cf5cf7dd12b98672435db2225a860f199d8/include/os/security_config.h) supplies the query functions and most flags. 25F70 adds the MTE flag. Apple documents the flag and uses it in XNU. An intermediate LLVM review included a fallback value of `0x4` that the merged change replaced with the system declaration. The released Apple OSS definition remains unlocated. [Apple API](https://developer.apple.com/documentation/os/os_security_config_t) · [XNU MTE test](https://github.com/apple-oss-distributions/xnu/blob/ac9718fb1af618d5ce8678d0dc6e8a58f252216f/tests/arm_mte_api.c) · [LLVM review mail](https://www.mail-archive.com/lldb-commits%40lists.llvm.org/msg128031.html) |
| `tgmath.h` | [Pinned Clang](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/clang/lib/Headers/tgmath.h) provides a tested C fallback on both architectures. Apple OSS search found compiler headers. The Darwin sysroot implementation remains unlocated. |
| `sandbox.h` | Apple’s [`sandbox_init(3)` manual](https://man.freebsd.org/cgi/man.cgi?manpath=macOS+26.7&query=sandbox_init&sektion=3) documents the deprecated public declarations, flag usage, and named profiles. Confirm the numeric flag value and exported object declarations independently to qualify a local header. The Apple OSS filename search found no corresponding public header. |
| `os/signpost.h` | [Apple’s C API documentation](https://developer.apple.com/documentation/os/os_signpost_emit_with_type) and [LLVM’s signpost consumer](https://github.com/llvm/llvm-project/blob/85ac560262434c9ccfc0c183ec22d4138ed647fb/llvm/lib/Support/Signposts.cpp) establish the public macro surface. A complete public C header still needs evidence for the macro lowering, backing ABI, and dependencies such as `os/trace_base.h`. Apple OSS search found the distinct XNU kernel signpost API. |

The matching distribution contains no standalone SIMD or XPC component.
The Apple OSS organization filename search found no corresponding public C
header set. The decision ledger records both omissions for 25F70 and preserves
the exact path sets. The discovery fixture still exercises both families.
[PureDarwin XPC](https://github.com/PureDarwin/XPC) and
[Darling libxpc](https://github.com/darlinghq/darling-libxpc) provide
reimplementations with six and seven of the 11 SDK header paths, respectively.
Matching names alone give no evidence about declaration or ABI coverage.
