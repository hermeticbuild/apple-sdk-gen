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
full_sources="$inputs/sources/$sdk-full"
llvm=${LLVM_DIR:-"$inputs/llvm"}
c_install="$out/c"
objc_install="$out/objc4"
frameworks="$out/frameworks"
simd_install="$out/simd"
generated_frameworks="$generated/System/Library/Frameworks"

test -x "$llvm/bin/clang" || { echo "Run make prepare to install LLVM at $llvm." >&2; exit 1; }
clang="$llvm/bin/clang"
bash tools/fetch_docc_snapshot.sh "$lock" "$inputs/docc" "$inputs/downloads" --verify
python3 -m components.simd.generate_headers --cache-dir "$inputs/docc" --out "$simd_install"

framework_inputs=()
selected_recipes="Cocoa AVFoundation CoreGraphics QuartzCore ApplicationServices IOKit Security SystemConfiguration AudioToolbox AudioUnit CoreAudio CoreAudioTypes CoreMIDI OpenAL"
requested=
if [[ -n ${FRAMEWORKS:-} ]]; then
  read -r -a names <<< "${FRAMEWORKS//,/ }"
  requested="${names[*]:-}"
  [[ -n $requested ]] || { echo "FRAMEWORKS must name at least one framework." >&2; exit 2; }
  selected_recipes=
  for name in "${names[@]}"; do
    [[ $name =~ ^[A-Za-z0-9_][A-Za-z0-9_.+-]*$ ]] || { echo "Invalid framework name: $name" >&2; exit 2; }
    framework_inputs+=(--framework "$name")
    if [[ -f "$repo/frameworks/$name/Makefile" ]]; then
      selected_recipes="${selected_recipes:+$selected_recipes }$name"
    fi
  done
fi

/usr/bin/sandbox-exec -f release/c-header-build.sb \
  make install SDK="$sdk" OUT="$c_install" SOURCE_ROOT="$sources" CLANG="$clang"
make install-objc4 SDK="$sdk" OUT="$objc_install" SOURCE_ROOT="$full_sources"

if [[ -n $selected_recipes ]]; then
  core_services_tbd="$generated_frameworks/CoreServices.framework/CoreServices.tbd"
  [[ -f $core_services_tbd ]] || core_services_tbd=
  make -C frameworks install SDK="$sdk" SOURCE_LOCK="$lock" \
    SOURCE_ROOT="$full_sources" OUT="$frameworks" \
    CLANG="$clang" C_INSTALL="$c_install" OBJC4_INSTALL="$objc_install" \
    GENERATED_FRAMEWORKS="$generated_frameworks" \
    FOUNDATION_TBD="$generated_frameworks/Foundation.framework/Foundation.tbd" \
    COCOA_FRAMEWORK="$generated_frameworks/Cocoa.framework" \
    COREGRAPHICS_FRAMEWORK="$generated_frameworks/CoreGraphics.framework" \
    CORE_SERVICES_TBD="$core_services_tbd" \
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
  --simd-install "$simd_install" --sdk-gen "$generated" --llvm "$llvm" --lock "$lock" "${stubs[@]}")
"${compose[@]}" --variant minimal --out "$out/MacOSX-Minimal.sdk"
for name in libc++ libc++.1 libc++abi libobjc libobjc.A; do
  compose+=(--external-stub "usr/lib/$name.tbd=$generated/usr/lib/$name.tbd")
done

for bundle in "$frameworks"/*.framework; do
  [[ -d $bundle ]] || continue
  name=$(basename "$bundle" .framework)
  [[ -z $requested || " $requested " == *" $name "* ]] || continue
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
python3 -m tools.sdk_composition.write_minimal_sdk_provenance "$out/MacOSX-Minimal.sdk" \
  --sources "$sources" --lock "$lock"
for sdk_tree in MacOSX-Minimal.sdk MacOSX.sdk; do
  python3 -m tools.pack_archive --source "$out/$sdk_tree" \
    --root-name MacOSX.sdk --output "$out/$sdk_tree.tar.zst"
done
