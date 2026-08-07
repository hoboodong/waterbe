# AGENTS.md

## Project Overview

Waterbe is an operations-analysis system for a seafood meal-kit and retail business operating in three E-mart stores.

| Store ID | Store |
| --- | --- |
| `store_wangsimni` | 왕십리점 |
| `store_mapo` | 마포점 |
| `store_wolgye` | 월계점 |

Supabase is the source of truth. Apps and sales sources collect data into Supabase; Waterbe connects and analyzes it. YAML sales files remain a legacy sales workspace.

Before changing data:

- Read `WATERBE_GUIDE.md` before changing business data.
- Read `PERSONNEL_GUIDE.md` before changing staff or schedule data.
- Read `instances/sales/README.md` before answering sales questions.

## Repository Layout

### Core Files

| Path | Purpose |
| --- | --- |
| `schema.yaml` | Supabase-backed operational data structure. |
| `WATERBE_GUIDE.md` | Waterbe system and analysis guide. |
| `PERSONNEL_GUIDE.md` | Staff, schedule, and Telegram permission rules. |

### Data Directories

| Path | Purpose |
| --- | --- |
| `instances/master/` | Legacy reference data retained for migration. |
| `instances/staff.yaml` | Staff and Telegram role data. |
| `instances/schedules.yaml` | Work and operational schedules. |
| `instances/inventory/` | Store inventory snapshots and inbound records. |
| `instances/sales/` | Sales-only workspace. |
| `scripts/` | Sales sync and query scripts. |

## Data Editing Rules

### Legacy YAML Rules

- Do not add new operational records to legacy YAML without explicit user instruction.
- Preserve the existing YAML shape: top-level `instances:` containing records with `id`, `class`, `data`, and optional `relations`.
- Use existing IDs and names exactly when creating references. Check the target file before adding a relation.
- Dates must use `YYYY-MM-DD`. Quote date strings when nearby files do so.
- Do not overwrite historical business records unless the user explicitly asks for correction of erroneous data.
- Preserve Korean business labels and comments.
- Do not reformat large YAML files just to make a small data change.

### Historical Records

- Keep Supabase operational records append-only where possible.
- Preserve recipe, price, purchase, inventory, production, and expense dates for analysis.

### Staff Rules

- `Staff.telegramId` must remain unique.
- `role: 팀장` uses `relations.atStore: null`.
- `role: 직원` requires a store.

## ID Conventions

| Record Type | Pattern |
| --- | --- |
| Staff | `staff_001`, `staff_002`, ... |
| Schedule | `sched_001`, `sched_002`, ... |
| Inventory snapshot | `snap_{store-abbrev}_YYYYMMDD_{ingredient-abbrev}` |
| Inbound record | `inbound_{store-abbrev}_YYYYMMDD_{sequence}` |

For new Supabase records, use app-generated IDs for products, ingredients, and recipes.

### Store Abbreviations

| Abbreviation | Store |
| --- | --- |
| `wg` | 월계점 |

Use the established abbreviation already present in the target file for other stores.

## Script Notes

- Scripts are Python 3 CLIs and use PyYAML where YAML parsing is needed.
- `scripts/namseon_sales.py` stores generated SQLite files under `instances/sales/namseon/`; `*.db`, `*.db-shm`, and `*.db-wal` are ignored by git.
- `scripts/namseon_drive_sync.py` depends on the external `gog` CLI for Google Drive and Sheets operations.
- Some scripts default to `~/.openclaw/shared/waterbe` for local operational data. When working in this repository, verify whether the user intends repo-local files or that shared path.

## Sales Query Rules

- For sales questions, start from `instances/sales/README.md`.
- For Namseon, Google Drive, or monthly store sales questions, query `instances/sales/namseon/namseon_sales.db` through `scripts/namseon_sales.py` instead of scanning Drive repeatedly.
- If the user says new Drive files were added or asks to sync sales, run the sync wrapper first. It scans both Google Drive root and the Namseon sales folder, imports new files, moves root-level source sales files into the matching monthly folder, and uploads the DB:

```bash
scripts/namseon_sync_now.sh
```

- For duplicate dates, keep only the selected latest Google Sheets source chosen by `scripts/namseon_drive_sync.py`.
- When the user asks to exclude products, pass each keyword with `--exclude`.
- If a value is net of a 20% commission and the user asks for the gross amount, calculate `net / 0.8`.
- When answering sales summaries that may be pasted into Telegram, avoid wide Markdown tables. Use compact text blocks that stay readable on mobile:

```text
2025 추석 전후 매출 비교
행사매출 제외 / 10월 9일 데이터 없음

[합계 순위]
1위 왕십리점 16,644,428원
2위 미아점 9,977,145원

[구간별 매출]
왕십리점
전 3일 11,762,690원 / 당일 2,005,848원 / 후 2일 2,875,890원
```

## Validation

Run lightweight validation after edits:

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

for path in sorted(Path('.').glob('**/*.yaml')):
    if '.git' in path.parts:
        continue
    with path.open(encoding='utf-8') as f:
        yaml.safe_load(f)
    print(path)
PY
```

For Namseon sales changes, also run the relevant CLI command, for example:

```bash
python3 scripts/namseon_sales.py --help
```

## Collaboration Notes

- Keep changes narrowly scoped to the user request.
- Before deleting, renaming, or rewriting records, confirm the intent unless the request is explicit.
