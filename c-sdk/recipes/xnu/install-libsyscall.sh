#!/bin/sh
# Stage the headers selected by Libsyscall's Xcode rules and the os/log.h exception.
set -eu
stage=$1
unifdef=$2
decomment="$(dirname "$0")/decomment.pl"
xnu=$SOURCE_ROOT/xnu
flags=$(cat "$stage/work/public-flags")
filtered="$stage/work/libsyscall.h"
mach_install=libsyscall/xcodescripts/mach_install_mig.sh
project=libsyscall/Libsyscall.xcodeproj/project.pbxproj

stage_header() {
    path=usr/include/$1
    source=$2
    rule=$3
    selection=$4
    output="$stage/dst/$path"
    mkdir -p "${output%/*}"
    # Split the flags emitted by XNU's Make rules; -x2 accepts both filtered
    # and unchanged inputs as success.
    "$unifdef" -x2 $flags "$xnu/$source" > "$filtered"
    /usr/bin/perl "$decomment" "$filtered" r > "$filtered.stripped"
    test -s "$filtered.stripped" || return 0
    (set -C; cat "$filtered" > "$output")
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$path" xnu "derived:sources/xnu/$source" "$selection" "macOS public unifdef" \
        "sources/xnu/$source" "sources/xnu/$rule" \
        sources/xnu/makedefs/MakeInc.cmd sources/xnu/makedefs/MakeInc.def sources/xnu/makedefs/MakeInc.rule \
        recipes/xnu/decomment.pl
}

mach_headers=$(awk '
    /^MACH_HDRS="/ { sub(/^MACH_HDRS="/, ""); reading=1 }
    reading {
        last = sub(/"$/, "")
        for (i = 1; i <= NF; i++) {
            if ($i !~ /^[[:alnum:]_]+\.h$/ || seen[$i]++) exit 1
            print $i
            count++
        }
        if (last) { reading=0; complete=1 }
    }
    END { if (!complete || !count) exit 1 }
' "$xnu/$mach_install")

{
    for name in $mach_headers; do
        stage_header "mach/$name" "libsyscall/mach/mach/$name" "$mach_install" "xnu/$mach_install:MACH_HDRS"
    done
    stage_header gethostuuid.h libsyscall/wrappers/gethostuuid.h "$project" "$project:macosx"
    stage_header spawn.h libsyscall/wrappers/spawn/spawn.h "$project" "$project:macosx"
    stage_header libproc.h libsyscall/wrappers/libproc/libproc.h "$project" "$project:macosx"
    # The pinned userspace list omits this header; compiler-rt uses its userspace branch.
    stage_header os/log.h libkern/os/log.h libkern/os/Makefile libkern/os/Makefile:userspace-exception
} >> "$stage/records"
