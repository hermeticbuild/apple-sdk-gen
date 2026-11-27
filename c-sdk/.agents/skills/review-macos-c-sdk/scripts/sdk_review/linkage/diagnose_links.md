# Diagnose a macOS link failure

Use the linker diagnostic to identify the undefined Mach-O name. Look it up
in both the [reference SDK and the assembled SDK](lookup_tbd_symbols.md).
Compile the failing client with its original include paths and flags. Set
`CLIENT_OBJECT` to that object and `ARCH` to its target architecture.

```sh
python3 -m sdk_review.linkage.verify_libsystem_links --llvm "$LLVM" --reference "$APPLE_SDK" \
  --candidate "$COMPOSED_SDK" --arch "$ARCH" --minimum 11.0 --sdk-version 26.5 \
  --object "$CLIENT_OBJECT" --out "$WORK/paired-$ARCH.json"
```

Use the failing client's deployment minimum and SDK version. This command
reports how the same object links through libSystem in each SDK, including
its weak imports and the library names recorded in the binaries.
