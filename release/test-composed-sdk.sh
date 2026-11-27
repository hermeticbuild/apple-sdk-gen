#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 ]]; then
  echo "Usage: $0 SDK_LOCK OUTPUT_DIRECTORY" >&2
  exit 2
fi
sdk=$(basename "$1" .json)
out=$(cd "$2" && pwd -P)
cd "$(dirname "$0")/.."
inputs=${INPUTS:-"$PWD/build/inputs"}
llvm=${LLVM_DIR:-"$inputs/llvm"}
test -x "$llvm/bin/clang" || { echo "Run make prepare to install LLVM at $llvm." >&2; exit 1; }
args=(CLANG="$llvm/bin/clang" SDK="$out/MacOSX.sdk" RUN=1)
make test SDK="$sdk" CLANG="$llvm/bin/clang" OUT="$out/c"

work=$(mktemp -d "${TMPDIR:-/tmp}/composed-sdk-tests.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
mkdir "$work/c" "$work/full"
tar -xf "$out/MacOSX-Minimal.sdk.tar.zst" -C "$work/c"
tar -xf "$out/MacOSX.sdk.tar.zst" -C "$work/full"
c_sdk="$work/c/MacOSX.sdk"
python3 -m tools.sdk_composition.c_sdk "$c_sdk" --compare "$work/full/MacOSX.sdk"
make -C tests/composed_sdk test test-c-libraries test-simd \
  CLANG="$llvm/bin/clang" SDK="$c_sdk" RUN=1

printf 'int main(void) { return 0; }\n' > "$work/client.c"
"$llvm/bin/clang" --no-default-config -target arm64-apple-macos11 -isysroot "$c_sdk" \
  -fuse-ld=lld -nostdlib -Wl,-Z -L"$c_sdk/usr/lib" -lSystem "$work/client.c" -o "$work/client"
"$work/client"
if "$llvm/bin/clang" --no-default-config -target arm64-apple-macos11 -isysroot "$c_sdk" \
  -fuse-ld=lld -nostdlib -Wl,-Z -L"$c_sdk/usr/lib" -lSystem -framework Foundation \
  "$work/client.c" -o "$work/framework-client" 2>"$work/framework.log"; then
  echo "C SDK unexpectedly linked Foundation." >&2
  exit 1
fi
grep -F 'framework not found for -framework Foundation' "$work/framework.log"

# The expanded fixture suite also tracks the known AVRouting and MetalKit gaps.
make -C frameworks test test-objc test-CoreServices test-ApplicationServices \
  test-CoreGraphics test-CoreVideo test-CoreMedia test-AVFoundation test-QuartzCore "${args[@]}"
make -C tests/composed_sdk test test-foundation-macros test-coregraphics \
  test-security test-network test-simd test-modelio test-modelio-modules \
  test-objc-property "${args[@]}"
LLVM="$llvm" LIBSYSTEM_TEST_LLVM="$llvm" \
  LIBSYSTEM_TEST_OBJC4="$out/objc4" ICONV_SOURCE="$inputs/sources/$sdk/libiconv" C_INSTALL="$out/c" \
  python3 -m unittest tools.sdk_composition.test_compose_sdk components.libiconv.test_stubs
