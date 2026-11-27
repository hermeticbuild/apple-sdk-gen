#!/bin/sh
# Merge finished producer stages into a new public include tree.
set -eu
export LC_ALL=C
bootstrap=false
if [ "$1" = --bootstrap ]; then bootstrap=true; shift; fi
out=$1
shift
fail() { echo "$*" >&2; exit 1; }
test -n "${SOURCE_ROOT:-}" || fail "SOURCE_ROOT is required to resolve producer inputs"
test ! -e "$out" && test ! -L "$out" || fail "output already exists: $out"
parent=$(dirname "$out")
mkdir -p "$parent"
scratch=$(mktemp -d "$parent/.apple-headers.XXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
tree="$scratch/tree"
mkdir "$tree"
tab=$(printf '\t')
test "$#" -gt 0 || fail "no producer stages"

for records do
    test -s "$records" || fail "empty stage: $records"
    include=$(realpath "$(dirname "$records")/dst/usr/include")

    # A producer must record exactly the headers it staged.
    (cd "$include" && find . -name '*.h' \( -type f -o -type l \) -print) > "$scratch/found"
    sed 's|^\./|usr/include/|' "$scratch/found" | sort > "$scratch/actual"
    cut -f1 "$records" | sort > "$scratch/declared"
    cmp -s "$scratch/actual" "$scratch/declared" || fail "stage paths differ from records: $records"

    while IFS= read -r row; do
        # Split the row on tabs only. Spaces in provenance remain literal.
        IFS="$tab"; set -f; set -- $row; set +f; unset IFS
        test "$#" -ge 6 || fail "invalid header record: $row"
        path=$1
        case "$path" in
            *[!a-zA-Z0-9_.+/-]*|*//*|*/../*|*/./*) fail "invalid header record: $path" ;;
            usr/include/*.h) ;;
            *) fail "invalid header record: $path" ;;
        esac
        # Rejoining also detects empty fields collapsed by shell splitting.
        normalized=$(printf '%s\t' "$@")
        test "${normalized%"$tab"}" = "$row" || fail "empty field for: $path"
        for field do
            case "$field" in *[[:cntrl:]]*) fail "invalid field for: $path" ;; esac
        done
        shift 5
        for input do
            case "$input" in
                */../*|*/..|*/./*|*/.) fail "invalid producer input: $input" ;;
                sources/*) test -f "$SOURCE_ROOT/${input#sources/}" || fail "missing producer input: $input" ;;
                recipes/*) test -f "$input" || fail "missing producer input: $input" ;;
                *) fail "invalid producer input: $input" ;;
            esac
        done
        source=$(realpath "$include/${path#usr/include/}")
        case "$source" in "$include"/*) ;; *) fail "header escapes stage: $path" ;; esac
        test -f "$source" || fail "staged header is not a file: $path"
        test ! -e "$tree/$path" || fail "multiple owners for $path"
        directory="$tree/${path%/*}"
        test -d "$directory" || mkdir -p "$directory"
        install -m 0644 "$source" "$tree/$path"
        if ! "$bootstrap"; then printf '%s\n' "$row" >> "$scratch/rows"; fi
    done < "$records"
done

if ! "$bootstrap"; then
    (cd "$tree" && find usr/include -type f -exec shasum -a 256 {} +) > "$scratch/hashes"
    # shasum prints "digest  path". Join path-tab-digest to the producer records.
    sed -E "s/^([0-9a-f]+)  (.*)$/\2$tab\1/" "$scratch/hashes" | sort -t "$tab" -k1,1 > "$scratch/by-path"
    sort -t "$tab" -k1,1 "$scratch/rows" > "$scratch/records"
    join -t "$tab" "$scratch/by-path" "$scratch/records" > "$scratch/manifest"
    test "$(wc -l < "$scratch/manifest")" = "$(wc -l < "$scratch/records")" ||
        fail "installed hashes do not cover the producer records"
    {
        printf 'path\tsha256\towner\torigin\tselection\ttransform\tinputs...\n'
        cat "$scratch/manifest"
    } > "$tree/header-manifest.tsv"
    if [ -n "${SOURCE_LOCK:-}" ]; then
        cp "$SOURCE_LOCK" "$tree/source-lock.json"
    fi
fi
mv "$tree" "$out"
