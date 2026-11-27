#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 3 && $# != 4 ]] || [[ ${4:-} != "" && $4 != --offline ]]; then
  echo "Usage: $0 SDK_LOCK CACHE_DIR DOWNLOAD_DIR [--offline]" >&2
  exit 2
fi

read -r expected key < <("${PYTHON:-python3}" -c '
import json, sys
with open(sys.argv[1]) as lock:
    docc = json.load(lock)["docc"]
print(docc["sha256"], docc["key"])
' "$1")

mkdir -p "$2" "$3"
cache_dir=$(cd "$2" && pwd -P)
download_dir=$(cd "$3" && pwd -P)
db="$cache_dir/cache.db"
receipt="$cache_dir/.snapshot-sha256"
archive="$download_dir/$expected.db.zst"

if [[ -e $db || -e $db-wal || -e $db-shm ]]; then
  if [[ -s $db && -f $receipt && $(cat "$receipt") == "$expected" ]]; then
    exit 0
  fi
  echo "DocC directory does not contain the pinned snapshot: $cache_dir" >&2
  exit 1
fi

check_digest() {
  local digest
  digest=$(shasum -a 256 "$1" | cut -d ' ' -f 1)
  if [[ $digest != "$expected" ]]; then
    echo "DocC snapshot checksum mismatch: $1" >&2
    exit 1
  fi
}

scratch=$(mktemp -d "$cache_dir/docc.XXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
if [[ ! -f $archive ]]; then
  if [[ ${4:-} == --offline ]]; then
    echo "Offline mode requires cached input: $archive" >&2
    exit 1
  fi
  : "${DOCC_R2_ENDPOINT:?Set DOCC_R2_ENDPOINT}"
  : "${DOCC_R2_BUCKET:?Set DOCC_R2_BUCKET}"
  : "${AWS_ACCESS_KEY_ID:?Set the DocC R2 access key secret}"
  : "${AWS_SECRET_ACCESS_KEY:?Set the DocC R2 secret access key}"
  export AWS_DEFAULT_REGION=auto AWS_EC2_METADATA_DISABLED=true
  aws --endpoint-url "$DOCC_R2_ENDPOINT" --no-cli-pager s3 cp \
    "s3://$DOCC_R2_BUCKET/$key" "$scratch/cache.db.zst" --only-show-errors
  check_digest "$scratch/cache.db.zst"
  mv "$scratch/cache.db.zst" "$archive"
else
  check_digest "$archive"
fi
zstd -dq "$archive" -o "$scratch/cache.db"
printf '%s\n' "$expected" > "$receipt"
mv "$scratch/cache.db" "$db"
echo "Restored DocC snapshot $key (SHA-256 $expected)"
