#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 {restore|save} CACHE_DIR" >&2
  exit 2
}

[[ $# == 2 && ( $1 == restore || $1 == save ) ]] || usage
operation=$1

: "${SDK_VERSION:?Set SDK_VERSION}"
: "${DOCC_R2_ENDPOINT:?Set DOCC_R2_ENDPOINT}"
: "${DOCC_R2_BUCKET:?Set DOCC_R2_BUCKET}"
: "${DOCC_R2_SNAPSHOT_KEY:?Set DOCC_R2_SNAPSHOT_KEY}"
: "${AWS_ACCESS_KEY_ID:?Set the DocC R2 access key secret}"
: "${AWS_SECRET_ACCESS_KEY:?Set the DocC R2 secret access key}"
export AWS_DEFAULT_REGION=auto AWS_EC2_METADATA_DISABLED=true

prefix="macos/$SDK_VERSION/snapshots/"
if [[ $DOCC_R2_SNAPSHOT_KEY != "$prefix"*.db.zst ]]; then
  echo "Expected the DocC seed key under $prefix" >&2
  exit 2
fi

mkdir -p "$2"
cache_dir=$(cd "$2" && pwd)
db="$cache_dir/cache.db"
count_file="$cache_dir/.docc-response-count"
scratch=$(mktemp -d "$cache_dir/docc.XXXXXX")
trap 'rm -rf -- "$scratch"' EXIT

s3() {
  aws --endpoint-url "$DOCC_R2_ENDPOINT" --no-cli-pager "$@"
}

response_count() {
  test -f "$1" && sqlite3 "$1" 'SELECT count(*) FROM cache;'
}

snapshot_digest() {
  shasum -a 256 "$1" | cut -d ' ' -f 1
}

if [[ $operation == restore ]]; then
  if [[ -e $db || -e $db-wal || -e $db-shm ]]; then
    echo "Expected an empty DocC cache directory at $cache_dir" >&2
    exit 1
  fi
  key=$(s3 s3api list-objects-v2 --bucket "$DOCC_R2_BUCKET" --prefix "$prefix" \
    --query 'max_by((Contents || `[]`)[?ends_with(Key, `.db.zst`)], &LastModified).Key' \
    --output json | jq -r '. // empty')
  key=${key:-$DOCC_R2_SNAPSHOT_KEY}
  expected=${key%.db.zst}
  expected=${expected##*-}
  s3 s3 cp "s3://$DOCC_R2_BUCKET/$key" "$scratch/cache.db.zst" --only-show-errors
  digest=$(snapshot_digest "$scratch/cache.db.zst")
  if [[ ! $expected =~ ^([0-9a-f]{12}|[0-9a-f]{64})$ || $digest != "$expected"* ]]; then
    echo "DocC snapshot checksum mismatch for $key" >&2
    exit 1
  fi
  zstd -dq "$scratch/cache.db.zst" -o "$scratch/cache.db"
  count=$(response_count "$scratch/cache.db")
  if (( count == 0 )); then
    echo "DocC snapshot contains no responses" >&2
    exit 1
  fi
  mv "$scratch/cache.db" "$db"
  printf '%s\n' "$count" > "$count_file"
  echo "Restored $count DocC responses from $key (SHA-256 $digest)"
else
  before=$(cat "$count_file")
  after=$(response_count "$db")
  if (( after < before )); then
    echo "The DocC cache lost responses ($before -> $after)" >&2
    exit 1
  elif (( after == before )); then
    echo "The DocC cache already contains all $after responses"
    exit 0
  fi

  (cd "$scratch" && sqlite3 "$db" '.backup cache.db')
  sqlite3 "$scratch/cache.db" 'PRAGMA journal_mode=DELETE;' >/dev/null
  zstd -q -T0 "$scratch/cache.db" -o "$scratch/cache.db.zst"
  digest=$(snapshot_digest "$scratch/cache.db.zst")
  key="$prefix$(date -u +%Y-%m-%d)-${GITHUB_RUN_ID:?Set GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT:?Set GITHUB_RUN_ATTEMPT}-$digest.db.zst"
  s3 s3 cp "$scratch/cache.db.zst" "s3://$DOCC_R2_BUCKET/$key" --only-show-errors
  echo "Saved $after DocC responses to $key (SHA-256 $digest)"
fi
