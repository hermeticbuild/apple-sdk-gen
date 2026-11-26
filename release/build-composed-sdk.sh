#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 3 ]]; then
  echo "Usage: $0 C_SDK REPLAY_INPUTS OUTPUT_DIRECTORY" >&2
  exit 2
fi
c_sdk=$(cd "$1" && pwd -P)
inputs=$(cd "$2" && pwd -P)
repo=$(cd "$(dirname "$0")/.." && pwd -P)
pin=$(cat "$repo/release/c-sdk.commit")
if [[ $(git -C "$c_sdk" rev-parse HEAD) != "$pin" ]] ||
  [[ -n $(git -C "$c_sdk" status --porcelain) ]]; then
  echo "Use a clean C SDK checkout at $pin." >&2
  exit 1
fi
out=$(mkdir -p "$3" && cd "$3" && pwd -P)
cd "$repo"

export PYTHONPATH="$PWD:$c_sdk"
sdk=macosx26.5
sources="$out/sources"
objc_sources="$out/objc-sources"
c_install="$out/c"
objc_install="$out/objc4"
frameworks="$out/frameworks"
generated="$out/generated"

source_cache=${C_SOURCE_CACHE:-"$PWD/build/c-source-cache"}
llvm_cache=${LLVM_CACHE:-"$PWD/build/llvm-cache"}
libcxx_cache=${LIBCXX_CACHE:-"$PWD/cache"}
framework_sources=${FRAMEWORK_SOURCE_ROOT:-"$PWD/build/framework-sources"}

(
  cd "$c_sdk"
  python3 -m tools.sources.locked_sources prepare --sdk "$sdk" --source-root "$sources" --cache "$source_cache"
  python3 -m tools.sources.locked_sources prepare --sdk "$sdk" --profile objc4 --source-root "$objc_sources" --cache "$source_cache"
)
llvm=${LLVM_DIR:-$(cd "$c_sdk" && python3 -m tools.toolchain.official_llvm prepare --cache "$llvm_cache")}
clang="$llvm/bin/clang"
make -C "$c_sdk" install SDK="$sdk" OUT="$c_install" SOURCE_ROOT="$sources" CLANG="$clang"
make -C "$c_sdk" install-objc4 SDK="$sdk" OUT="$objc_install" SOURCE_ROOT="$objc_sources"

# The saved framework base and three generated donors preserve the tested
# inputs. Rebuild the Darwin stubs and C++ headers with SDK Gen's producers.
mkdir "$generated"
cp "$inputs/generated/SDKSettings.json" "$generated/"
python3 - "$generated" "$libcxx_cache" <<'PY'
import sys
from pathlib import Path
from tools.apple_sdk_gen.supplements.darwin_libs import install_darwin_lib_stubs, select_darwin_libraries
from tools.apple_sdk_gen.supplements.libcxx import install_libcxx_headers

sdk = Path(sys.argv[1])
install_darwin_lib_stubs(sdk, select_darwin_libraries("26.5", None))
install_libcxx_headers(sdk, "26.5", Path(sys.argv[2]))
PY

# Only these four staged bundles enter the overlay. The other targets
# declared here supply their Make dependencies and build inputs.
make -C frameworks prepare SOURCE_ROOT="$framework_sources"
make -C frameworks install SOURCE_ROOT="$framework_sources" OUT="$frameworks" \
  CLANG="$clang" C_INSTALL="$c_install" OBJC4_INSTALL="$objc_install" SDK_GEN_SOURCE="$PWD" \
  FOUNDATION_TBD="$inputs/Foundation.tbd" CORE_SERVICES_TBD="$inputs/CoreServices.tbd" \
  COREGRAPHICS_FRAMEWORK="$inputs/CoreGraphics.framework" \
  FRAMEWORKS="Cocoa AVFoundation CoreGraphics QuartzCore ApplicationServices IOKit"

python3 -m tools.sdk_composition.iconv_stubs --source "$sources/libiconv" \
  --c-install "$c_install" --llvm "$llvm" --out "$out/iconv"
make -C stubs/libresolv C_SDK="$c_sdk" SOURCE_ROOT="$sources" \
  C_INSTALL="$c_install" CLANG="$clang" OUT="$out/resolver"

stubs=()
for name in libc++ libc++.1 libc++abi libobjc libobjc.A; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$generated/usr/lib/$name.tbd")
done
stubs+=(--external-stub "usr/lib/libz.tbd=$inputs/frameworks/usr/lib/libz.tbd")
for name in libiconv libiconv.2 libcharset libcharset.1; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$out/iconv/usr/lib/$name.tbd")
done
for name in libresolv libresolv.9; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$out/resolver/usr/lib/$name.tbd")
done

overlays=()
for name in AppKit CoreFoundation Foundation IOKit; do
  overlays+=(--framework-overlay "$name" "$frameworks/$name.framework")
done

python3 -m tools.sdk_composition.compose_sdk \
  --c-install "$c_install" --objc4-install "$objc_install" \
  --sdk-gen "$generated" --framework-sdk-gen "$inputs/frameworks" \
  --all-frameworks --include-cxx --llvm "$llvm" "${overlays[@]}" "${stubs[@]}" \
  --out "$out/MacOSX.sdk"
python3 -m tools.pack_archive --source "$out/MacOSX.sdk" \
  --root-name MacOSX.sdk --output "$out/MacOSX.sdk.tar.zst"
