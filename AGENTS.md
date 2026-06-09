# AGENTS.md

## Project Overview

Waterbe is a YAML-first operations data repository for a seafood meal-kit and retail business operating in three E-mart stores.

| Store ID | Store |
| --- | --- |
| `store_wangsimni` | 왕십리점 |
| `store_mapo` | 마포점 |
| `store_wolgye` | 월계점 |

The source of truth is the YAML data under `instances/`, with the ontology and field definitions in `schema.yaml`.

Before changing data:

- Read `WATERBE_GUIDE.md` before changing business data.
- Read `PERSONNEL_GUIDE.md` before changing staff or schedule data.
- Read `instances/sales/README.md` before answering sales questions.

## Repository Layout

### Core Files

| Path | Purpose |
| --- | --- |
| `schema.yaml` | Ontology schema, classes, relations, and constraints. |
| `WATERBE_GUIDE.md` | Business data guide for products, ingredients, recipes, inventory, production, and sales. |
| `PERSONNEL_GUIDE.md` | Staff, schedule, and Telegram permission rules. |

### Data Directories

| Path | Purpose |
| --- | --- |
| `instances/master/` | Baseline master data: stores, categories, products, ingredients, purchase specs, price history, and recipes. |
| `instances/staff.yaml` | Staff and Telegram role data. |
| `instances/schedules.yaml` | Work and operational schedules. |
| `instances/inventory/` | Store inventory snapshots and inbound records. |
| `instances/production/` | Production plans and production templates. |
| `instances/sales/` | Sales-only workspace. |
| `scripts/` | Operational import, export, sync, and calculation scripts. |

## Data Editing Rules

### General YAML Rules

- Preserve the existing YAML shape: top-level `instances:` containing records with `id`, `class`, `data`, and optional `relations`.
- Use existing IDs and names exactly when creating references. Check the target file before adding a relation.
- Dates must use `YYYY-MM-DD`. Quote date strings when nearby files do so.
- Do not overwrite historical business records unless the user explicitly asks for correction of erroneous data.
- Preserve Korean business labels and comments.
- Do not reformat large YAML files just to make a small data change.

### Historical Records

| Class | Rule |
| --- | --- |
| `PriceHistory` | Add a new record for a price change. Do not edit older price history records to represent a new price. |
| `Recipe` | Preserve history with `effectiveFrom` and `effectiveTo` when recipe, price, or ingredient amounts change. |
| `ProductionTemplate` | Close the current active record by setting `effectiveTo` to the day before the new `effectiveFrom`, then add a new record with `effectiveTo: null`. |
| `ProductionPlan` | Do not change `dailyPlan` after creation. Put changes in `dailyAdjusted`, and actuals in `dailyActual`. |
| `InventorySnapshot` / `InboundRecord` | Append a new record for each new count or receipt. |

### Staff Rules

- `Staff.telegramId` must remain unique.
- `role: 팀장` uses `relations.atStore: null`.
- `role: 직원` requires a store.

## ID Conventions

| Record Type | Pattern |
| --- | --- |
| Staff | `staff_001`, `staff_002`, ... |
| Schedule | `sched_001`, `sched_002`, ... |
| Production plan | `plan_{store-abbrev}_YYYYMMDD_{product-abbrev}` |
| Inventory snapshot | `snap_{store-abbrev}_YYYYMMDD_{ingredient-abbrev}` |
| Inbound record | `inbound_{store-abbrev}_YYYYMMDD_{sequence}` |

For product, ingredient, purchase spec, recipe, template, and price history IDs, follow the existing per-file conventions.

### Store Abbreviations

| Abbreviation | Store |
| --- | --- |
| `wg` | 월계점 |

Use the established abbreviation already present in the target file for other stores.

## Script Notes

- Scripts are Python 3 CLIs and use PyYAML where YAML parsing is needed.
- `scripts/namseon_sales.py` stores generated SQLite files under `instances/sales/namseon/`; `*.db`, `*.db-shm`, and `*.db-wal` are ignored by git.
- `scripts/namseon_drive_sync.py` depends on the external `gog` CLI for Google Drive and Sheets operations.
- `scripts/sync_to_supabase.py` requires `SUPABASE_URL` and `SUPABASE_KEY`.
- `scripts/export_github_data.py` can update GitHub when `GITHUB_TOKEN` is set.
- Some scripts default to `~/.openclaw/shared/waterbe` for local operational data. When working in this repository, verify whether the user intends repo-local files or that shared path.

## Sales Query Rules

- For sales questions, start from `instances/sales/README.md`.
- For Namseon, Google Drive, or monthly store sales questions, query `instances/sales/namseon/namseon_sales.db` through `scripts/namseon_sales.py` instead of scanning Drive repeatedly.
- If the user says new Drive files were added, run the incremental sync first:

```bash
python3 scripts/namseon_drive_sync.py --incremental --trash-duplicates --upload-db
```

- For duplicate dates, keep only the selected latest Google Sheets source chosen by `scripts/namseon_drive_sync.py`.
- When the user asks to exclude products, pass each keyword with `--exclude`.
- If a value is net of a 20% commission and the user asks for the gross amount, calculate `net / 0.8`.

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
