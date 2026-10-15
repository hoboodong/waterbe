"""Read a complete Wolgye month from the verified sales store (GET only)."""
import argparse
import calendar
from datetime import date, datetime, timezone
import json

from waterbe_api import call

ALIASES = {"EM월계점", "SFM월계점"}


def summarize(month, read=call):
    first = date.fromisoformat(month + "-01")
    entries, closed, missing, failures = [], [], [], []
    source_ids, imported = [], []
    for day in range(1, calendar.monthrange(first.year, first.month)[1] + 1):
        current = first.replace(day=day)
        key = current.isoformat()
        result = read("sales.daeyoung.read", key)
        if result["status"] not in {"available", "missing_source"}:
            failures.append(key)
            continue
        regular_closed = current.weekday() == 6 and 8 <= day <= 14 or current.weekday() == 6 and 22 <= day <= 28
        sources = result["data"]["sources"]
        rows = [r for r in result["data"]["rows"] if r["store"] in ALIASES]
        source_ids.extend(s["file_id"] for s in sources)
        imported.extend(s["imported_at"] for s in sources if s.get("imported_at"))
        if not rows:
            (closed if regular_closed else missing).append(key)
            continue
        review = any(s["validation_status"] != "verified" for s in sources)
        entries.append({"date": key, "amount": sum(r["amount"] for r in rows),
                        "validation_status": "review_required" if review else "verified"})
    return {"status": "unavailable" if failures else "available", "month": month,
            "store": "월계점", "source": "Supabase daeyoung_sales_sources/rows",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "latest_imported_at": max(imported, default=None),
            "source_ids": source_ids, "sales_days": len(entries),
            "total_sales": sum(e["amount"] for e in entries),
            "verified_sales": sum(e["amount"] for e in entries if e["validation_status"] == "verified"),
            "review_sales": sum(e["amount"] for e in entries if e["validation_status"] != "verified"),
            "review_dates": [e["date"] for e in entries if e["validation_status"] != "verified"],
            "closed_dates": closed, "missing_dates": missing, "failed_dates": failures,
            "daily_sales": entries, "fee_basis": "이마트 수수료 21.5% 차감 후 대영매출"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True)
    args = parser.parse_args()
    try:
        result = summarize(args.month)
    except (ValueError, TypeError):
        result = {"status": "invalid_request", "reason": "Use YYYY-MM"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "available" else 1


if __name__ == "__main__":
    raise SystemExit(main())
