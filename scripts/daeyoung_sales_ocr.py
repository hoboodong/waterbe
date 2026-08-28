#!/usr/bin/env python3
"""Extract daily Daeyoung sales-table screenshots with local PaddleOCR."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from datetime import date
from pathlib import Path


DATE_RE = re.compile(r"(?P<month>\d{1,2})/(?P<day>\d{1,2})")
AMOUNT_RE = re.compile(r"^\d{1,3}(?:,\d{3})*$")
STORE_CORRECTIONS = {
    # A recurring narrow-font OCR miss in the source screenshots.
    "EM계점": "EM월계점",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def parse_table(texts: list[str], year: int) -> tuple[str | None, list[dict], int | None]:
    date_match = next((DATE_RE.search(text) for text in texts if DATE_RE.search(text)), None)
    sales_date = None
    if date_match:
        sales_date = date(
            year, int(date_match.group("month")), int(date_match.group("day"))
        ).isoformat()

    rows: list[dict] = []
    index = 0
    while index + 2 < len(texts):
        store, tax_type, amount_text = texts[index : index + 3]
        store = STORE_CORRECTIONS.get(store, store)
        if (
            store.startswith("EM")
            and tax_type in {"면세", "과세"}
            and AMOUNT_RE.fullmatch(amount_text)
        ):
            rows.append(
                {
                    "store": store,
                    "tax_type": tax_type,
                    "amount": int(amount_text.replace(",", "")),
                }
            )
            index += 3
        else:
            index += 1

    amount_tokens = [
        int(text.replace(",", "")) for text in texts if AMOUNT_RE.fullmatch(text)
    ]
    stated_total = amount_tokens[-1] if amount_tokens else None
    return sales_date, rows, stated_total


def is_wolgye_regular_closed_day(sales_date: str | None) -> bool:
    """Wolgye is closed on the second and fourth Sunday of every month."""
    if sales_date is None:
        return False
    value = date.fromisoformat(sales_date)
    sunday_number = (value.day - 1) // 7 + 1
    return value.weekday() == 6 and sunday_number in {2, 4}


def main() -> int:
    args = parse_args()
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    from paddleocr import PaddleOCR

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    names = {
        item["drive_id"]: item.get("name", item.get("drive_name", item["drive_id"]))
        for item in manifest
    }
    images = sorted(path for path in args.input_dir.iterdir() if path.is_file())
    ocr = PaddleOCR(
        lang="korean",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
    )

    extracted: list[dict] = []
    file_reports: list[dict] = []
    for number, image_path in enumerate(images, 1):
        result = list(ocr.predict(str(image_path)))[0]
        texts = list(result["rec_texts"])
        scores = [float(value) for value in result["rec_scores"]]
        sales_date, rows, stated_total = parse_table(texts, args.year)
        calculated_total = sum(row["amount"] for row in rows)
        wolgye_rows = [row for row in rows if "월계" in row["store"]]
        regular_closed = is_wolgye_regular_closed_day(sales_date)
        source_name = names.get(image_path.stem, image_path.name)
        for row in rows:
            extracted.append(
                {
                    "date": sales_date or "",
                    "store": row["store"],
                    "tax_type": row["tax_type"],
                    "amount": row["amount"],
                    "source_name": source_name,
                    "drive_id": image_path.stem,
                }
            )
        issues = []
        if sales_date is None:
            issues.append("date_not_found")
        if stated_total != calculated_total:
            issues.append("total_mismatch")
        if not wolgye_rows and not regular_closed:
            issues.append("wolgye_not_found")
        if scores and min(scores) < 0.8:
            issues.append("low_confidence_text")
        file_reports.append(
            {
                "date": sales_date,
                "source_name": source_name,
                "drive_id": image_path.stem,
                "row_count": len(rows),
                "stated_total": stated_total,
                "calculated_total": calculated_total,
                "wolgye": wolgye_rows,
                "wolgye_regular_closed": regular_closed,
                "min_confidence": round(min(scores), 4) if scores else None,
                "issues": issues,
            }
        )
        print(f"[{number}/{len(images)}] {sales_date or image_path.name}: {', '.join(issues) or 'OK'}", flush=True)

    extracted.sort(key=lambda row: (row["date"], row["store"], row["tax_type"]))
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["date", "store", "tax_type", "amount", "source_name", "drive_id"],
        )
        writer.writeheader()
        writer.writerows(extracted)

    report = {
        "image_count": len(images),
        "recognized_dates": sorted(
            item["date"] for item in file_reports if item["date"] is not None
        ),
        "issue_count": sum(bool(item["issues"]) for item in file_reports),
        "files": sorted(file_reports, key=lambda item: item["date"] or "9999"),
    }
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
