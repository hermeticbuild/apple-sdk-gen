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
    printf '%s\t%s\t%s\t%s\t%s\t%s' \
        "$path" "$owner" "staged:$owner:$relative" "$rule" "$transform" "$rule"
    for input do printf '\t%s' "$input"; done
    printf '\n'
done < "$stage/installed-paths"
