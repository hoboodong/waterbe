#!/usr/bin/env bash
set -euo pipefail
root="${WATERBE_ROOT:-$HOME/waterbe}"
python_bin="${WATERBE_PYTHON:-$HOME/.local/opt/waterbe-central-venv/bin/python}"
export PATH="$HOME/.local/bin:$HOME/.local/gog-bin:/usr/bin:/bin:${PATH:-}"
set -a
source <(tr -d '\r' < "$HOME/.config/waterbe/central.env")
set +a
export CAS_CL5200_BACKUP_ROOT="$HOME/.local/state/cas-supervisor/snapshots"
export CAS_CL5200_LOG_ROOT="$HOME/.local/state/waterbe-central/logs"
cd "$root"
command="${1:-status}"
if (($#)); then shift; fi
case "$command" in
  manage) exec "$python_bin" "$root/scripts/central_manage.py" "$@" ;;
  status)
    systemctl --user show waterbe-history.service caspi-remote-read.service cas-supervisor.service cas-aggregate-sync.service caspi-receipt-sync.service cas-telegram-reporter.service -p Id -p ActiveState -p SubState -p ExecMainStatus
    "$python_bin" "$root/scripts/history_worker.py" --database "$HOME/.local/state/waterbe-history/operations.db" status
    ;;
  api) exec "$python_bin" "$root/scripts/waterbe_api.py" "$@" ;;
  namseon-check) exec "$python_bin" "$root/scripts/namseon_drive_sync.py" --incremental --include-drive-root --dry-run "$@" ;;
  namseon-sync)
    exec flock -n "$HOME/.local/state/waterbe-central/namseon-sync.lock" "$python_bin" "$root/scripts/namseon_drive_sync.py" --incremental --include-drive-root --organize-root-files --trash-duplicates --sync-supabase --upload-db "$@"
    ;;
  daeyoung-ocr) exec "$python_bin" "$root/scripts/daeyoung_sales_ocr.py" --det-model PP-OCRv5_mobile_det --rec-model korean_PP-OCRv5_mobile_rec --cpu-threads 1 "$@" ;;
  daeyoung-publish) exec "$python_bin" "$root/scripts/daeyoung_supabase_sync.py" "$@" ;;
  backup) exec "$python_bin" "$root/scripts/central_backup.py" "$@" ;;
  *) printf 'Unknown central command: %s\n' "$command" >&2; exit 2 ;;
esac
