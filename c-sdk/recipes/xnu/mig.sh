#!/bin/sh
# Public macOS Libsyscall MIG headers. Follow mach_install_mig.sh's MIGS list
# and use its attribute filter after preprocessing with the pinned Clang.
set -eu

mig=$1
clang=$2
sysroot=$3
test -d "$sysroot/usr/include" || { echo "MIG sysroot missing: $sysroot" >&2; exit 1; }
stage=$4
out="$stage/dst/usr/include"
xnu="$SOURCE_ROOT/xnu"
libsyscall="$xnu/libsyscall"
script="$libsyscall/xcodescripts/mach_install_mig.sh"

names=$(awk '
    /^MIGS="/ { sub(/^MIGS="/, ""); reading=1 }
    reading {
        last = sub(/"$/, "")
        for (i = 1; i <= NF; i++) {
            if ($i !~ /^[[:alnum:]_]+\.defs$/ || seen[$i]++) exit 1
            print $i
            count++
        }
        if (last) { reading=0; complete=1 }
    }
    /MIGS="\$MIGS mach_vm\.defs"/ { vm=1 }
    END { if (!complete || !count || !vm || seen["mach_vm.defs"]) exit 1 }
' "$script")
test ! -e "$stage"
mkdir -p "$out/mach"
for defs in $names mach_vm.defs; do
    header="$out/mach/${defs%.defs}.h"
    # Libsyscall preprocesses its ARM definitions in MIG's armv7 mode.
    "$mig" -cc "$clang" -novouchers -arch armv7 -isysroot "$sysroot" \
        "-I$xnu/osfmk" -DLIBSYSCALL_INTERFACE -user /dev/null -server /dev/null \
        -header "$header" "$libsyscall/mach/$defs"
    awk -f "$libsyscall/xcodescripts/filter_mig.awk" \
        "$libsyscall/mach/add_attributes_to_mig.txt" "$header" > "$header.filtered"
    mv "$header.filtered" "$header"
    name=$(basename "$header")
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "usr/include/mach/$name" xnu "generated:system-mig:$name via recipes/xnu/mig.sh" \
        "xnu/libsyscall/xcodescripts/mach_install_mig.sh:public" \
        "system MIG for arm64, then filter" recipes/xnu/mig.sh \
        "sources/xnu/libsyscall/mach/$defs" \
        sources/xnu/libsyscall/xcodescripts/filter_mig.awk \
        sources/xnu/libsyscall/mach/add_attributes_to_mig.txt \
        sources/xnu/libsyscall/xcodescripts/mach_install_mig.sh >> "$stage/records"
done
