#!/bin/sh
# Record the public outputs of an Apple install command.
set -eu
stage=$1 owner=$2 rule=$3 scope=$4 exclude=$5
shift 5
case "$rule" in
    sources/*) transform="Apple public header install" ;;
    *) transform="producer header install recipe" ;;
esac

cd "$stage/dst"
find "$scope" -name '*.h' ! -path "$exclude" \( -type f -o -type l \) -print > "$stage/installed-paths"
while IFS= read -r path; do
    relative=${path#usr/include/}
    # The upstream install rules retain the basename except for the
    # availability header, which CMake installs from os_availability.h.
    case "$owner/$relative" in
        AvailabilityVersions/os/availability.h) input=templates/os_availability.h ;;
        AvailabilityVersions/*) input="templates/$relative" ;;
        architecture/architecture/*) input=${relative#architecture/} ;;
        CarbonHeaders/AssertMacros.h) input=AssertMacros.h ;;
        Libc/execinfo.h|Libc/get_compat.h) input="gen/$relative" ;;
        Libc/nl_types.h) input=include/FreeBSD/nl_types.h ;;
        Libc/tzfile.h) input=stdtime/FreeBSD/tzfile.h ;;
        Libc/utmpx.h) input=include/NetBSD/utmpx.h ;;
        Libc/*) input="include/$relative" ;;
        Libinfo/ifaddrs.h) input=gen.subproj/ifaddrs.h ;;
        Libinfo/membership.h|Libinfo/ntsid.h) input="membership.subproj/$relative" ;;
        Libinfo/rpc/*) input="rpc.subproj/${relative#rpc/}" ;;
        Libinfo/rpcsvc/*) input="nis.subproj/${relative#rpcsvc/}" ;;
        Libinfo/*) input="lookup.subproj/$relative" ;;
        libdispatch/os/*) input="$relative" ;;
        libpthread/sys/*) input="include/$relative" ;;
        libpthread/*) input="include/pthread/$relative" ;;
        *) printf 'No install source for %s/%s\n' "$owner" "$relative" >&2; exit 1 ;;
    esac
    source="sources/$owner/$input"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s' \
        "$path" "$owner" "derived:$source" "$rule" "$transform" "$rule" "$source"
    for input do printf '\t%s' "$input"; done
    printf '\n'
done < "$stage/installed-paths"
