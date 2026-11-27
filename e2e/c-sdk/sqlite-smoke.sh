#!/usr/bin/env bash
set -euo pipefail

sqlite=$1
work=$(mktemp -d "${TMPDIR:-/tmp}/sqlite-c-sdk.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
db="$work/test.db"

# The CLI and engine are compiled from BCR sources. The only dynamic
# library needed by the resulting executable is macOS libSystem.
dependencies=$(/usr/bin/otool -L "$sqlite" | awk 'NR > 1 {print $1}')
[[ "$dependencies" == /usr/lib/libSystem.B.dylib ]]
[[ $("$sqlite" -batch -bail "$db" \
  'PRAGMA journal_mode=WAL; CREATE TABLE items(n); BEGIN; INSERT INTO items VALUES (10),(32); COMMIT;') == wal ]]
[[ $("$sqlite" -batch -bail "$db" 'SELECT SUM(n) FROM items; PRAGMA integrity_check;') == $'42\nok' ]]
echo "SQLite committed, reopened, and checked a database using the C SDK."
