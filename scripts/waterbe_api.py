"""Discover Waterbe interfaces and read sales originals without synchronization.

Only allowlisted GET adapters execute here. Native and planned entries are discovery
metadata, not callable implementations. No credentials or server error bodies are logged.
"""
import argparse
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config/api_catalog.json"
TABLES = {"sales.namseon.read": "namseon", "sales.daeyoung.read": "daeyoung"}


def catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def read_table(base, key, table, business_date):
    rows = []
    for offset in range(0, 100000, 500):
        query = urlencode({"select": "*", "sale_date": "eq." + business_date,
                           "order": "file_id" if table.endswith("sources") else "source_file_id,row_number",
                           "offset": offset, "limit": 500})
        request = Request(base + "/rest/v1/" + table + "?" + query,
                          headers={"apikey": key, "Authorization": "Bearer " + key}, method="GET")
        with urlopen(request, timeout=20) as response:
            page = json.load(response)
        if not isinstance(page, list):
            raise ValueError("Invalid response")
        rows.extend(page)
        if len(page) < 500:
            return rows
    raise ValueError("Pagination incomplete")


def call(operation, business_date):
    result = {"operation": operation, "status": "unavailable", "business_date": business_date,
              "fetched_at": datetime.now(timezone.utc).isoformat(), "data": None}
    if operation not in TABLES:
        result.update(status="unsupported", reason="Use catalog entry and required guide; no gateway adapter.")
        return result
    date.fromisoformat(business_date)
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or not key:
        result["reason"] = "HTTPS SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required."
        return result
    prefix = TABLES[operation] + "_sales"
    try:
        sources = read_table(base, key, prefix + "_sources", business_date)
        rows = read_table(base, key, prefix + "_rows", business_date)
        # Re-read source versions: do not silently combine two import generations.
        if sources != read_table(base, key, prefix + "_sources", business_date):
            result["reason"] = "Source changed during read; retry required."
            return result
        source_ids = {source["file_id"] for source in sources}
        if any(row["source_file_id"] not in source_ids for row in rows) or sum(s["row_count"] for s in sources) != len(rows):
            result["reason"] = "Source/row completeness check failed."
            return result
        result.update(status="available" if sources else "missing_source",
                      source=prefix, data={"sources": sources, "rows": rows},
                      warnings=["Raw sales originals only; not a production or integrated report.",
                                "Missing source does not prove zero sales. Latest ingestion not independently verified."])
    except Exception:
        result["reason"] = "Source read or validation failed; no zero substituted. Check credentials, connectivity and schema."
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    describe = sub.add_parser("describe")
    describe.add_argument("operation")
    invoke = sub.add_parser("call")
    invoke.add_argument("operation")
    invoke.add_argument("--date", required=True)
    args = parser.parse_args()
    if args.command == "list":
        output = catalog()
    elif args.command == "describe":
        output = next((x for x in catalog()["operations"] if x["id"] == args.operation), {"status": "unknown_operation"})
    else:
        try:
            output = call(args.operation, args.date)
        except ValueError:
            output = {"status": "invalid_request", "reason": "Use ISO business date YYYY-MM-DD."}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output.get("status", "available") == "available" else 1


if __name__ == "__main__":
    raise SystemExit(main())
