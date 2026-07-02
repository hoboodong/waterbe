# AGENTS.md

## Project Overview

Waterbe is a YAML-first operations data repository for a seafood meal-kit and retail business operating in three E-mart stores.

| Store ID | Store |
| --- | --- |
| `store_wangsimni` | 왕십리점 |
| `store_mapo` | 마포점 |
| `store_wolgye` | 월계점 |

The source of truth is the YAML data under `instances/`. Field and relation definitions live only in `schema.yaml`; the guide documents (`WATERBE_GUIDE.md`, `PERSONNEL_GUIDE.md`) cover business rules and do not redefine fields.

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
| Product | `prod_{store-abbrev}_{product-alias}` |
| Recipe | `recipe_{store-abbrev}_{product-alias}` (revisions append `_2`, `_3`, …) |
| Production template | `tmpl_{store-abbrev}_{product-alias}` |
| Production plan | `plan_{store-abbrev}_YYYYMMDD_{product-alias}` |

Product alias: the cleaned product name if it is 5 characters or fewer,
otherwise a short alias. The authoritative alias table is the id ↔ name
mapping in `instances/master/products.yaml`.
| Inventory snapshot | `snap_{store-abbrev}_YYYYMMDD_{ingredient-abbrev}` |
| Inbound record | `inbound_{store-abbrev}_YYYYMMDD_{sequence}` |

For ingredient, purchase spec, and price history IDs, follow the existing per-file conventions.

### Store Abbreviations

| Abbreviation | Store |
| --- | --- |
| `ws` | 왕십리점 |
| `mp` | 마포점 |
| `wg` | 월계점 |

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

Run the validator after every data or schema edit:

```bash
python3 scripts/validate.py
```

It checks YAML parsing, record shape, global ID uniqueness, relation
reference integrity, required fields, date formats, and the business
constraints listed in `schema.yaml`. Errors must be fixed before commit;
warnings are informational.

For Namseon sales changes, also run the relevant CLI command, for example:

```bash
python3 scripts/namseon_sales.py --help
```

## Collaboration Notes

- Keep changes narrowly scoped to the user request.
- Before deleting, renaming, or rewriting records, confirm the intent unless the request is explicit.
