#!/usr/bin/env python3
"""Upload Daeyoung OCR result pairs to Supabase, one sale date at a time."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


IGNORED_REVIEW_ISSUES = {"wolgye_not_found"}


def configuration() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return url, key


def request_json(method: str, url: str, key: str, payload: dict | None = None) -> object:
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


def load_results(root: Path) -> list[tuple[dict, list[dict]]]:
    loaded_by_date: dict[str, tuple[dict, list[dict]]] = {}
    for report_path in sorted(root.rglob("*_report.json")):
        result_month = report_path.name[:7]
        expected_year, expected_month = (int(value) for value in result_month.split("-"))
        csv_path = report_path.with_name(report_path.name.replace("_report.json", "_sales.csv"))
        if not csv_path.exists():
            raise RuntimeError(f"matching CSV missing for {report_path}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rows_by_file: dict[str, list[dict]] = defaultdict(list)
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                rows_by_file[row["drive_id"]].append(row)

        for file_report in report["files"]:
            sale_date = file_report.get("date")
            if not sale_date:
                continue
            parsed_year, parsed_month, parsed_day = (int(value) for value in sale_date.split("-"))
            if parsed_month == expected_month:
                parsed_year = expected_year
            elif expected_month == 1 and parsed_month == 12:
                parsed_year = expected_year - 1
            elif expected_month == 12 and parsed_month == 1:
                parsed_year = expected_year + 1
            sale_date = f"{parsed_year:04d}-{parsed_month:02d}-{parsed_day:02d}"
            file_id = file_report["drive_id"]
            source_rows = sorted(
                rows_by_file.get(file_id, []),
                key=lambda row: (row["store"], row["tax_type"], int(row["amount"])),
            )
            rows = [
                {
                    "row_number": index,
                    "store": row["store"],
                    "tax_type": row["tax_type"],
                    "amount": int(row["amount"]),
                }
                for index, row in enumerate(source_rows, 1)
            ]
            issues = [
                issue
                for issue in file_report.get("issues", [])
                if issue not in IGNORED_REVIEW_ISSUES
            ]
            source = {
                "file_id": file_id,
                "file_name": file_report["source_name"],
                "sale_date": sale_date,
                "drive_url": f"https://drive.google.com/file/d/{file_id}/view",
                "stated_total": file_report.get("stated_total"),
                "calculated_total": file_report.get("calculated_total", 0),
                "min_confidence": file_report.get("min_confidence"),
                "validation_status": "review_required" if issues else "verified",
                "validation_issues": issues,
                "wolgye_regular_closed": bool(file_report.get("wolgye_regular_closed")),
            }
            existing = loaded_by_date.get(sale_date)
            if existing is None or source["file_name"] > existing[0]["file_name"]:
                loaded_by_date[sale_date] = (source, rows)
    return sorted(loaded_by_date.values(), key=lambda item: item[0]["sale_date"])


def verify(url: str, key: str, sale_date: str, expected: int) -> None:
    query = urlencode({"sale_date": f"eq.{sale_date}", "select": "row_count"})
    result = request_json("GET", f"{url}/rest/v1/daeyoung_sales_sources?{query}", key)
    actual = result[0]["row_count"] if isinstance(result, list) and len(result) == 1 else -1
    if actual != expected:
        raise RuntimeError(
            f"Supabase verification failed for {sale_date}: expected {expected}, got {actual}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        results = load_results(args.results_root)
        if args.dry_run:
            review = sum(source["validation_status"] == "review_required" for source, _ in results)
            print(f"dates={len(results)} review_required={review}")
            return
        url, key = configuration()
        for index, (source, rows) in enumerate(results, 1):
            result = request_json(
                "POST",
                f"{url}/rest/v1/rpc/replace_daeyoung_sales_date",
                key,
                {"p_source": source, "p_rows": rows},
            )
            if result != len(rows):
                raise RuntimeError(
                    f"RPC result mismatch for {source['sale_date']}: "
                    f"expected {len(rows)}, got {result}"
                )
            verify(url, key, source["sale_date"], len(rows))
            print(
                f"[{index}/{len(results)}] supabase {source['sale_date']} "
                f"rows={len(rows)} {source['validation_status']}"
            )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
