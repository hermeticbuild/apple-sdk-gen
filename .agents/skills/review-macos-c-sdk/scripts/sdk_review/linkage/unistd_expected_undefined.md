# macOS 26.5 expected-undefined unistd.h qualification

Run from the repository root with the approved SDK 26.5 build 25F70, the
matching generated C installation and the verified LLVM projection. Keep the
lookup and qualification receipts in a local work directory.

    python3 -m sdk_review.linkage.lookup_tbd_symbols --sdk "$APPLE_SDK" --llvm "$LLVM" \
      --raw-symbol _add_profil --raw-symbol _profil --raw-symbol _unwhiteout \
      --out "$WORK/unistd-sdk-lookup.json"
    python3 -m sdk_review.linkage.verify_unistd_expected_undefined \
      --sdk "$APPLE_SDK" --c-install "$C_INSTALL" --llvm "$LLVM" \
      --lookup "$WORK/unistd-sdk-lookup.json" --out "$WORK/unistd-qualification.json"

The [review policy](data/macosx26.5/expected-undefined.json) pins
the SDK build, installed header bytes and selected Libc source revision. The
qualification checks the header digest on each side and verifies complete
SDK-wide lookup coverage with all three raw names, including explicit
symbols, symbol forwards, linker directives and raw token matches.

For each name, the tool compiles a typed address reference using
`<unistd.h>` from the SDK and then from the standalone C installation. It
checks the exact Mach-O import and relocation. Each object is strictly linked
using the SDK's libSystem stub. The complete matrix covers both architectures
and deployment minima 11.0 and 26.5. Every case must report exactly the
expected missing symbol. A successful link, a different diagnostic or a
changed source, SDK or lookup requires review before keeping the omission.

The local receipt records the SDK identity, policy and lookup digests plus
each compilation, object evidence and link trace. It qualifies the reference
SDK link interface. Runtime presence and behavior are outside this check.
