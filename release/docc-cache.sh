#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 1 ]]; then
  echo "Usage: $0 CACHE_DIR" >&2
  exit 2
fi

: "${SDK_VERSION:?Set SDK_VERSION}"
: "${DOCC_R2_ENDPOINT:?Set DOCC_R2_ENDPOINT}"
: "${DOCC_R2_BUCKET:?Set DOCC_R2_BUCKET}"
: "${AWS_ACCESS_KEY_ID:?Set the DocC R2 access key secret}"
: "${AWS_SECRET_ACCESS_KEY:?Set the DocC R2 secret access key}"
export AWS_DEFAULT_REGION=auto AWS_EC2_METADATA_DISABLED=true

read -r expected key < "$(dirname "$0")/docc.snapshot"
if [[ ! $expected =~ ^[0-9a-f]{64}$ || $key != "macos/$SDK_VERSION/snapshots/"*.db.zst ]]; then
  echo "Invalid DocC snapshot pin for macOS $SDK_VERSION" >&2
  exit 2
fi

mkdir -p "$1"
cache_dir=$(cd "$1" && pwd)
db="$cache_dir/cache.db"
if [[ -e $db || -e $db-wal || -e $db-shm ]]; then
  echo "Expected an empty DocC cache directory at $cache_dir" >&2
  exit 1
fi

scratch=$(mktemp -d "$cache_dir/docc.XXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
aws --endpoint-url "$DOCC_R2_ENDPOINT" --no-cli-pager s3 cp \
  "s3://$DOCC_R2_BUCKET/$key" "$scratch/cache.db.zst" --only-show-errors
digest=$(shasum -a 256 "$scratch/cache.db.zst" | cut -d ' ' -f 1)
if [[ $digest != "$expected" ]]; then
  echo "DocC snapshot checksum mismatch for $key" >&2
  exit 1
fi
zstd -dq "$scratch/cache.db.zst" -o "$scratch/cache.db"
count=$(sqlite3 "$scratch/cache.db" 'SELECT count(*) FROM cache;')
if (( count == 0 )); then
  echo "DocC snapshot contains no responses" >&2
  exit 1
fi
mv "$scratch/cache.db" "$db"
echo "Restored $count DocC responses from $key (SHA-256 $digest)"
