#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 3 ]]; then
  echo "Usage: $0 SDK_LOCK GENERATED_SDK OUTPUT_DIRECTORY" >&2
  exit 2
fi
lock=$(cd "$(dirname "$1")" && printf "%s/%s\n" "$PWD" "$(basename "$1")")
generated=$(cd "$2" && pwd -P)
repo=$(cd "$(dirname "$0")/.." && pwd -P)
out=$(mkdir -p "$3" && cd "$3" && pwd -P)
cd "$repo"

sdk=$(basename "$lock" .json)
inputs=${INPUTS:-"$repo/build/inputs"}
sources="$inputs/sources/$sdk"
objc_sources="$inputs/sources/$sdk-objc4"
framework_sources="$inputs/sources/$sdk-frameworks"
llvm=${LLVM_DIR:-"$inputs/llvm"}
c_install="$out/c"
objc_install="$out/objc4"
frameworks="$out/frameworks"
generated_frameworks="$generated/System/Library/Frameworks"

test -x "$llvm/bin/clang" || { echo "Run make prepare to install LLVM at $llvm." >&2; exit 1; }
python3 -m tools.fetch_sources --verify --lock "${lock%.json}-frameworks.json" --dest "$framework_sources"
clang="$llvm/bin/clang"
/usr/bin/sandbox-exec -f release/c-header-build.sb \
  make install SDK="$sdk" OUT="$c_install" SOURCE_ROOT="$sources" CLANG="$clang"
make install-objc4 SDK="$sdk" OUT="$objc_install" SOURCE_ROOT="$objc_sources"

recipes="Cocoa AVFoundation CoreGraphics QuartzCore ApplicationServices IOKit Security SystemConfiguration AudioToolbox AudioUnit CoreAudio CoreAudioTypes CoreMIDI OpenAL"
selected_recipes="$recipes"
if [[ -n ${FRAMEWORKS:-} ]]; then
  selected_recipes=
  requested=",${FRAMEWORKS// /},"
  for name in $recipes Foundation AppKit CoreData; do
    if [[ -d "$generated_frameworks/$name.framework" || $requested == *,"$name",* ]]; then
      selected_recipes="${selected_recipes:+$selected_recipes }$name"
    fi
  done
fi
if [[ -n $selected_recipes ]]; then
  make -C frameworks install SOURCE_ROOT="$framework_sources" OUT="$frameworks" \
    CLANG="$clang" C_INSTALL="$c_install" OBJC4_INSTALL="$objc_install" \
    GENERATED_FRAMEWORKS="$generated_frameworks" \
    FOUNDATION_TBD="$generated_frameworks/Foundation.framework/Foundation.tbd" \
    COCOA_FRAMEWORK="$generated_frameworks/Cocoa.framework" \
    COREGRAPHICS_FRAMEWORK="$generated_frameworks/CoreGraphics.framework" \
    CORE_SERVICES_TBD="$generated_frameworks/CoreServices.framework/CoreServices.tbd" \
    FRAMEWORKS="$selected_recipes"
fi

python3 -m components.libiconv.generate_stubs --source "$sources/libiconv" \
  --c-install "$c_install" --llvm "$llvm" --out "$out/iconv"
make -f components/libresolv/stubs.mk SDK="$sdk" SOURCE_ROOT="$sources" \
  C_INSTALL="$c_install" CLANG="$clang" OUT="$out/resolver"

stubs=()
for name in libz libz.1 libbsm libbsm.0 libipsec libipsec.A; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$generated/usr/lib/$name.tbd")
done
for name in libiconv libiconv.2 libcharset libcharset.1; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$out/iconv/usr/lib/$name.tbd")
done
for name in libresolv libresolv.9; do
  stubs+=(--external-stub "usr/lib/$name.tbd=$out/resolver/usr/lib/$name.tbd")
done

compose=(python3 -m tools.sdk_composition.compose_sdk --c-install "$c_install"
  --sdk-gen "$generated" --llvm "$llvm" --lock "$lock" "${stubs[@]}")
"${compose[@]}" --variant minimal --out "$out/MacOSX-Minimal.sdk"
for name in libc++ libc++.1 libc++abi libobjc libobjc.A; do
  compose+=(--external-stub "usr/lib/$name.tbd=$generated/usr/lib/$name.tbd")
done

framework_inputs=()
for bundle in "$frameworks"/*.framework; do
  [[ -d $bundle ]] || continue
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

"${compose[@]}" --objc4-install "$objc_install" \
  --variant full "${framework_inputs[@]}" \
  --out "$out/MacOSX.sdk"
python3 -m tools.sdk_composition.c_sdk "$out/MacOSX-Minimal.sdk" --write-provenance "$sources" --lock "$lock"
for sdk_tree in MacOSX-Minimal.sdk MacOSX.sdk; do
  python3 -m tools.pack_archive --source "$out/$sdk_tree" \
    --root-name MacOSX.sdk --output "$out/$sdk_tree.tar.zst"
done
