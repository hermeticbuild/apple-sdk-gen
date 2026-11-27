#!/bin/sh
# XNU's Make stamp records unifdef arguments, ending in newline and NUL.
set -eu
path=$1
shift
tmp="$path.next"
printf '%s\n\000' "$*" > "$tmp"
if cmp -s "$tmp" "$path"; then
    /bin/rm "$tmp"
else
    /bin/mv "$tmp" "$path"
fi
