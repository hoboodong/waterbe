#!/usr/bin/env python3
"""
남선매출 일별 시트를 SQLite로 누적하고 조회한다.

사용:
  python3 scripts/namseon_sales.py init-db
  python3 scripts/namseon_sales.py import-csv /path/to/export.csv --date 2026-05-31 --source-file-id <drive-id>
  python3 scripts/namseon_sales.py month-total --store mapo --month 2026-05
  python3 scripts/namseon_sales.py month-total --store wangsimni --month 2026-05
  python3 scripts/namseon_sales.py month-total --store wangsimni --month 2026-05 --exclude 추가행사팀품목
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "instances" / "sales" / "namseon" / "namseon_sales.db"

STORE_ALIASES = {
    "mapo": "EM마포점",
    "wangsimni": "EM왕십리점",
    "wolgye": "EM월계점",
    "마포": "EM마포점",
    "마포점": "EM마포점",
    "왕십리": "EM왕십리점",
    "왕십리점": "EM왕십리점",
    "월계": "EM월계점",
    "월계점": "EM월계점",
}

EVENT_TEAM_PRODUCT_KEYWORDS = [
    "통낙지볶음",
    "갑오징어무침",
    "데친문어",
    "불맛주꾸미볶음",
]


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_files (
  file_id TEXT PRIMARY KEY,
  file_name TEXT NOT NULL,
  sale_date TEXT NOT NULL,
  modified_time TEXT,
  imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sales_rows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file_id TEXT NOT NULL REFERENCES source_files(file_id) ON DELETE CASCADE,
  row_number INTEGER NOT NULL,
  sale_date TEXT NOT NULL,
  store TEXT NOT NULL,
  product TEXT,
  daily_qty INTEGER NOT NULL DEFAULT 0,
  daily_sales INTEGER NOT NULL DEFAULT 0,
  month_qty INTEGER NOT NULL DEFAULT 0,
  month_sales INTEGER NOT NULL DEFAULT 0,
  is_store_total INTEGER NOT NULL DEFAULT 0,
  UNIQUE(source_file_id, row_number)
);

CREATE INDEX IF NOT EXISTS idx_sales_rows_date_store
  ON sales_rows(sale_date, store);

CREATE INDEX IF NOT EXISTS idx_sales_rows_store_product
  ON sales_rows(store, product);

CREATE UNIQUE INDEX IF NOT EXISTS idx_source_files_sale_date
  ON source_files(sale_date);
"""


@dataclass
class SalesRow:
    row_number: int
    sale_date: str
    store: str
    product: str | None
    daily_qty: int
    daily_sales: int
    month_qty: int
    month_sales: int
    is_store_total: int


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def parse_int(value: str | None) -> int:
    if value is None:
        return 0
    cleaned = str(value).strip().replace(",", "").replace(" ", "")
    if cleaned in {"", "-"}:
        return 0
    return int(float(cleaned))


def normalize_store(raw: str) -> tuple[str, bool]:
    text = raw.strip()
    if text.endswith(" 총계"):
        return text[:-3].strip(), True
    return text, False


def parse_csv(path: Path, sale_date: str) -> list[SalesRow]:
    rows: list[SalesRow] = []
    current_store = ""
    layout = "name"

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row_number, row in enumerate(reader, start=1):
            if len(row) < 4:
                continue
            first = row[0].strip()
            if first == "점포코드":
                layout = "code"
                continue

            if first == "점포명" or "상품명" in row:
                continue
            if not first and not current_store:
                continue

            if layout == "code":
                if len(row) < 7:
                    continue
                item_code = row[1].strip()
                product = row[2].strip()

                if first.endswith(" 총계"):
                    store = f"STORE_CODE:{first[:-3].strip()}"
                    current_store = store
                    rows.append(
                        SalesRow(
                            row_number=row_number,
                            sale_date=sale_date,
                            store=store,
                            product=None,
                            daily_qty=parse_int(row[3]),
                            daily_sales=parse_int(row[4]),
                            month_qty=parse_int(row[5]),
                            month_sales=parse_int(row[6]),
                            is_store_total=1,
                        )
                    )
                    continue

                if item_code.endswith(" 총계"):
                    continue

                if first:
                    current_store = f"STORE_CODE:{first}"
                store = current_store
                if not store or not product:
                    continue

                rows.append(
                    SalesRow(
                        row_number=row_number,
                        sale_date=sale_date,
                        store=store,
                        product=product,
                        daily_qty=parse_int(row[3]),
                        daily_sales=parse_int(row[4]),
                        month_qty=parse_int(row[5]),
                        month_sales=parse_int(row[6]),
                        is_store_total=0,
                    )
                )
                continue

            product = row[1].strip()

            is_total = False
            if first:
                store, is_total = normalize_store(first)
                current_store = store
            else:
                store = current_store

            if not store:
                continue

            rows.append(
                SalesRow(
                    row_number=row_number,
                    sale_date=sale_date,
                    store=store,
                    product=None if is_total else product,
                    daily_qty=parse_int(row[2]),
                    daily_sales=parse_int(row[3]),
                    month_qty=parse_int(row[4]) if len(row) > 4 else 0,
                    month_sales=parse_int(row[5]) if len(row) > 5 else 0,
                    is_store_total=1 if is_total else 0,
                )
            )

    return rows


def import_csv(
    db_path: Path,
    csv_path: Path,
    sale_date: str,
    source_file_id: str,
    source_file_name: str | None,
    modified_time: str | None,
) -> None:
    init_db(db_path)
    source_name = source_file_name or csv_path.name
    parsed_rows = parse_csv(csv_path, sale_date)
    imported_at = datetime.now().isoformat(timespec="seconds")

    with connect(db_path) as conn:
        conn.execute(
            "DELETE FROM source_files WHERE sale_date = ? AND file_id <> ?",
            (sale_date, source_file_id),
        )
        conn.execute(
            """
            INSERT INTO source_files(file_id, file_name, sale_date, modified_time, imported_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(file_id) DO UPDATE SET
              file_name = excluded.file_name,
              sale_date = excluded.sale_date,
              modified_time = excluded.modified_time,
              imported_at = excluded.imported_at
            """,
            (source_file_id, source_name, sale_date, modified_time, imported_at),
        )
        conn.execute("DELETE FROM sales_rows WHERE source_file_id = ?", (source_file_id,))
        conn.executemany(
            """
            INSERT INTO sales_rows(
              source_file_id, row_number, sale_date, store, product,
              daily_qty, daily_sales, month_qty, month_sales, is_store_total
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    source_file_id,
                    r.row_number,
                    r.sale_date,
                    r.store,
                    r.product,
                    r.daily_qty,
                    r.daily_sales,
                    r.month_qty,
                    r.month_sales,
                    r.is_store_total,
                )
                for r in parsed_rows
            ],
        )

    print(f"imported {len(parsed_rows)} rows from {source_name}")


def canonical_store(value: str) -> str:
    return STORE_ALIASES.get(value, value)


def latest_sale_date_for_month(conn: sqlite3.Connection, month: str) -> str | None:
    row = conn.execute(
        """
        SELECT MAX(sale_date)
        FROM sales_rows
        WHERE sale_date >= ? AND sale_date < ?
        """,
        (f"{month}-01", next_month(month)),
    ).fetchone()
    return row[0] if row else None


def next_month(month: str) -> str:
    year, mon = [int(x) for x in month.split("-")]
    if mon == 12:
        return f"{year + 1:04d}-01-01"
    return f"{year:04d}-{mon + 1:02d}-01"


def month_total(db_path: Path, store_key: str, month: str, extra_event_keywords: list[str]) -> None:
    store = canonical_store(store_key)
    event_keywords = EVENT_TEAM_PRODUCT_KEYWORDS + extra_event_keywords
    with connect(db_path) as conn:
        sale_date = latest_sale_date_for_month(conn, month)
        if not sale_date:
            raise SystemExit(f"no data for month: {month}")

        total_row = conn.execute(
            """
            SELECT month_sales
            FROM sales_rows
            WHERE sale_date = ? AND store = ? AND is_store_total = 1
            """,
            (sale_date, store),
        ).fetchone()
        if not total_row:
            raise SystemExit(f"no store total for {store} on {sale_date}")

        total = int(total_row[0])
        product_rows = conn.execute(
            """
            SELECT product, month_sales
            FROM sales_rows
            WHERE sale_date = ?
              AND store = ?
              AND is_store_total = 0
              AND product IS NOT NULL
            ORDER BY product
            """,
            (sale_date, store),
        ).fetchall()

        event_rows = [
            (product, int(amount))
            for product, amount in product_rows
            if any(keyword in product for keyword in event_keywords)
        ]

        event_sum = sum(amount for _, amount in event_rows)
        waterbe_sales = total - event_sum

    print(f"store={store}")
    print(f"month={month}")
    print(f"basis_date={sale_date}")
    print(f"total_sales={total:,}")
    print(f"event_team_default_keywords={', '.join(EVENT_TEAM_PRODUCT_KEYWORDS)}")
    if extra_event_keywords:
        print(f"event_team_extra_keywords={', '.join(extra_event_keywords)}")
    for product, amount in event_rows:
        print(f"event_team {product}: {amount:,}")
    print(f"event_team_sales={event_sum:,}")
    print(f"waterbe_sales={waterbe_sales:,}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="남선매출 SQLite import/query tool")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")

    import_parser = sub.add_parser("import-csv")
    import_parser.add_argument("csv_path", type=Path)
    import_parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    import_parser.add_argument("--source-file-id", required=True)
    import_parser.add_argument("--source-file-name")
    import_parser.add_argument("--modified-time")

    total_parser = sub.add_parser("month-total")
    total_parser.add_argument("--store", required=True)
    total_parser.add_argument("--month", required=True, help="YYYY-MM")
    total_parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        dest="extra_event_keywords",
        help="기본 행사팀 품목 외에 추가로 행사팀 매출로 분류할 상품명 키워드",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "init-db":
        init_db(args.db)
        print(f"initialized {args.db}")
    elif args.command == "import-csv":
        import_csv(
            args.db,
            args.csv_path,
            args.date,
            args.source_file_id,
            args.source_file_name,
            args.modified_time,
        )
    elif args.command == "month-total":
        month_total(args.db, args.store, args.month, args.extra_event_keywords)


if __name__ == "__main__":
    main()
