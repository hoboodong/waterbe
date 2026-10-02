#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/sdg/waterbe"
LOCK_FILE="/tmp/waterbe_namseon_sync.lock"

export PATH="$HOME/.local/gog-bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

SECRETS_FILE="$HOME/.config/sdg-secrets.env"
if [[ -f "$SECRETS_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SECRETS_FILE"
  set +a
fi

: "${SUPABASE_URL:?SUPABASE_URL is required}"
: "${SUPABASE_SERVICE_ROLE_KEY:?SUPABASE_SERVICE_ROLE_KEY is required}"
command -v gog >/dev/null

cd "$ROOT"

exec 9>"$LOCK_FILE"
flock -n 9

python3 scripts/namseon_drive_sync.py \
  --incremental \
  --include-drive-root \
  --organize-root-files \
  --trash-duplicates \
  --sync-supabase \
  --upload-db
