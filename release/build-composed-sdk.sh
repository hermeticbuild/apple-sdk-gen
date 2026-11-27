#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 2 ]]; then
  echo "Usage: $0 GENERATED_SDK OUTPUT_DIRECTORY" >&2
  exit 2
fi
generated=$(cd "$1" && pwd -P)
repo=$(cd "$(dirname "$0")/.." && pwd -P)
out=$(mkdir -p "$2" && cd "$2" && pwd -P)
cd "$repo"

sdk=macosx26.5
sources="$out/sources"
objc_sources="$out/objc-sources"
c_install="$out/c"
objc_install="$out/objc4"
frameworks="$out/frameworks"
generated_frameworks="$generated/System/Library/Frameworks"

source_cache=${C_SOURCE_CACHE:-"$PWD/build/c-source-cache"}
llvm_cache=${LLVM_CACHE:-"$PWD/build/llvm-cache"}
framework_sources=${FRAMEWORK_SOURCE_ROOT:-"$PWD/build/framework-sources"}

python3 -m tools.sources.locked_sources prepare --sdk "$sdk" --source-root "$sources" --cache "$source_cache"
python3 -m tools.sources.locked_sources prepare --sdk "$sdk" --profile objc4 --source-root "$objc_sources" --cache "$source_cache"
llvm=${LLVM_DIR:-$(python3 -m tools.toolchain.official_llvm prepare --cache "$llvm_cache")}
clang="$llvm/bin/clang"
make install SDK="$sdk" OUT="$c_install" SOURCE_ROOT="$sources" CLANG="$clang"
make install-objc4 SDK="$sdk" OUT="$objc_install" SOURCE_ROOT="$objc_sources"

make -C frameworks prepare SOURCE_ROOT="$framework_sources"
make -C frameworks install SOURCE_ROOT="$framework_sources" OUT="$frameworks" \
  CLANG="$clang" C_INSTALL="$c_install" OBJC4_INSTALL="$objc_install" \
  GENERATED_FRAMEWORKS="$generated_frameworks" \
  FOUNDATION_TBD="$generated_frameworks/Foundation.framework/Foundation.tbd" \
  COCOA_FRAMEWORK="$generated_frameworks/Cocoa.framework" \
  COREGRAPHICS_FRAMEWORK="$generated_frameworks/CoreGraphics.framework" \
  CORE_SERVICES_TBD="$generated_frameworks/CoreServices.framework/CoreServices.tbd" \
  FRAMEWORKS="Cocoa AVFoundation CoreGraphics QuartzCore ApplicationServices IOKit Security SystemConfiguration AudioToolbox AudioUnit CoreAudio CoreAudioTypes CoreMIDI OpenAL"

python3 -m components.libiconv.generate_stubs --source "$sources/libiconv" \
  --c-install "$c_install" --llvm "$llvm" --out "$out/iconv"
make -f components/libresolv/stubs.mk SOURCE_ROOT="$sources" \
  C_INSTALL="$c_install" CLANG="$clang" OUT="$out/resolver"

stubs=()
for name in libc++ libc++.1 libc++abi libobjc libobjc.A libz libz.1; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$generated/usr/lib/$name.tbd")
done
for name in libiconv libiconv.2 libcharset libcharset.1; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$out/iconv/usr/lib/$name.tbd")
done
for name in libresolv libresolv.9; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$out/resolver/usr/lib/$name.tbd")
done

framework_inputs=()
for bundle in "$frameworks"/*.framework; do
  name=$(basename "$bundle" .framework)
  case "$name" in
    IOKit|Security)
      framework_inputs+=(--framework-overlay "$name" "$bundle")
      ;;
    *)
      # A replacement module map must see only the matching recipe headers.
      framework_inputs+=(--prepared-framework "$name" "$bundle")
      ;;
  esac
done

python3 -m tools.sdk_composition.compose_sdk \
  --c-install "$c_install" --objc4-install "$objc_install" --sdk-gen "$generated" \
  --all-frameworks --include-cxx --llvm "$llvm" "${framework_inputs[@]}" "${stubs[@]}" \
  --out "$out/MacOSX.sdk"
python3 -m tools.pack_archive --source "$out/MacOSX.sdk" \
  --root-name MacOSX.sdk --output "$out/MacOSX.sdk.tar.zst"
