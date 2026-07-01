#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/sdg/waterbe"
LOCK_FILE="/tmp/waterbe_namseon_sync.lock"

export PATH="/usr/local/bin:/usr/bin:/bin:${PATH:-}"

cd "$ROOT"

exec 9>"$LOCK_FILE"
flock -n 9

python3 scripts/namseon_drive_sync.py \
  --incremental \
  --include-drive-root \
  --organize-root-files \
  --trash-duplicates \
  --upload-db
