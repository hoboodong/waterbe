#!/usr/bin/env python3
"""Upload the verified Namseon SQLite ledger to Supabase, one sale date at a time."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "instances" / "sales" / "namseon" / "namseon_sales.db"


def configuration() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise SystemExit(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required "
            "(SUPABASE_KEY is accepted for compatibility)"
        )
    return url, key


def request_json(
    method: str, url: str, key: str, payload: dict | None = None
) -> object:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Supabase connection failed: {exc.reason}") from exc
    return json.loads(raw) if raw else None


def available_dates(conn: sqlite3.Connection, requested: list[str]) -> list[str]:
    if requested:
        missing = [
            value
            for value in requested
            if not conn.execute(
                "SELECT 1 FROM source_files WHERE sale_date = ?", (value,)
            ).fetchone()
        ]
        if missing:
            raise SystemExit(f"sale dates not found in SQLite: {', '.join(missing)}")
        return sorted(set(requested))
    return [row[0] for row in conn.execute("SELECT sale_date FROM source_files ORDER BY sale_date")]


def load_date(conn: sqlite3.Connection, sale_date: str) -> tuple[dict, list[dict]]:
    conn.row_factory = sqlite3.Row
    source = conn.execute(
        """
        SELECT file_id, file_name, sale_date, modified_time
        FROM source_files WHERE sale_date = ?
        """,
        (sale_date,),
    ).fetchone()
    if not source:
        raise RuntimeError(f"source missing for {sale_date}")
    rows = conn.execute(
        """
        SELECT row_number, store, product, daily_qty, daily_sales,
               month_qty, month_sales, is_store_total
        FROM sales_rows WHERE source_file_id = ? ORDER BY row_number
        """,
        (source["file_id"],),
    ).fetchall()
    return dict(source), [
        {**dict(row), "is_store_total": bool(row["is_store_total"])} for row in rows
    ]


def verify(url: str, key: str, sale_date: str, expected: int) -> None:
    query = urlencode({"sale_date": f"eq.{sale_date}", "select": "row_count"})
    result = request_json("GET", f"{url}/rest/v1/namseon_sales_sources?{query}", key)
    actual = result[0]["row_count"] if isinstance(result, list) and len(result) == 1 else -1
    if actual != expected:
        raise RuntimeError(
            f"Supabase verification failed for {sale_date}: expected {expected}, got {actual}"
        )


def sync(db: Path, dates: list[str], dry_run: bool) -> None:
    if not db.exists():
        raise SystemExit(f"SQLite DB not found: {db}")
    url, key = ("", "") if dry_run else configuration()
    with sqlite3.connect(db) as conn:
        selected = available_dates(conn, dates)
        if not selected:
            print("supabase_sync_dates=0")
            return
        for index, sale_date in enumerate(selected, start=1):
            source, rows = load_date(conn, sale_date)
            if dry_run:
                print(f"[{index}/{len(selected)}] would-sync {sale_date} rows={len(rows)}")
                continue
            result = request_json(
                "POST",
                f"{url}/rest/v1/rpc/replace_namseon_sales_date",
                key,
                {"p_source": source, "p_rows": rows},
            )
            if result != len(rows):
                raise RuntimeError(
                    f"RPC result mismatch for {sale_date}: expected {len(rows)}, got {result}"
                )
            verify(url, key, sale_date, len(rows))
            print(f"[{index}/{len(selected)}] supabase {sale_date} rows={len(rows)} verified")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Namseon SQLite sales to Supabase")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--date", action="append", default=[], help="YYYY-MM-DD; repeatable")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        sync(args.db, args.date, args.dry_run)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
