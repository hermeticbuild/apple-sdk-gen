#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 ]]; then
  echo "Usage: $0 C_SDK OUTPUT_DIRECTORY" >&2
  exit 2
fi
c_sdk=$(cd "$1" && pwd -P)
out=$(cd "$2" && pwd -P)
cd "$(dirname "$0")/.."
llvm_cache=${LLVM_CACHE:-"$PWD/build/llvm-cache"}
llvm=${LLVM_DIR:-$(cd "$c_sdk" && python3 -m tools.toolchain.official_llvm prepare --offline --cache "$llvm_cache")}
args=(CLANG="$llvm/bin/clang" SDK="$out/MacOSX.sdk" RUN=1)
make -C "$c_sdk" test CLANG="$llvm/bin/clang" OUT="$out/c"
# The expanded fixture suite also tracks the known AVRouting and MetalKit gaps.
make -C frameworks test test-objc test-CoreServices test-ApplicationServices \
  test-CoreGraphics test-CoreVideo test-CoreMedia test-AVFoundation test-QuartzCore "${args[@]}"
make -C tests/composed_sdk test test-foundation-macros test-coregraphics \
  test-security test-network test-simd test-modelio test-modelio-modules \
  test-objc-property C_SDK="$c_sdk" "${args[@]}"
PYTHONPATH="$PWD:$c_sdk" LLVM="$llvm" LIBSYSTEM_TEST_LLVM="$llvm" \
  LIBSYSTEM_TEST_OBJC4="$out/objc4" ICONV_SOURCE="$out/sources/libiconv" C_INSTALL="$out/c" \
  python3 -m unittest discover -s tools/sdk_composition
