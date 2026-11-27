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
PYTHONPATH="$PWD" python3 tests/sdk_archives/compare_sdk_archives.py "$c_sdk" "$work/full/MacOSX.sdk"
make -C tests/minimal_sdk_linking test \
  CLANG="$llvm/bin/clang" SDK="$c_sdk" RUN=1
make -C tests/minimal_sdk_linking test-dns-sd test-resolver test-simd "${args[@]}"
make -C frameworks test test-objc test-CoreServices test-ApplicationServices \
  test-CoreGraphics test-CoreVideo test-CoreMedia test-AVFoundation test-QuartzCore \
  test-AppKit-exports test-AppKit-image test-fsevents "${args[@]}"
make -C tests/full_sdk_frameworks test "${args[@]}"
LLVM="$llvm" LIBSYSTEM_TEST_LLVM="$llvm" \
  ICONV_SOURCE="$inputs/sources/$sdk/libiconv" C_INSTALL="$out/c" \
  python3 -m unittest tools.sdk_composition.test_compose_sdk components.libiconv.test_stubs
