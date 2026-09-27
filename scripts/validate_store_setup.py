"""Read-only validation of the local store registry and dated team visits.

This checks configuration, not live SeaCode/CAS connectivity or sales attribution.
Requires PyYAML, as do the existing Waterbe YAML tools.
"""

import argparse
import re
from datetime import date
from pathlib import Path

import yaml


def _required_text(data, key, context):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: {key} must be nonempty text")
    return value


def _day(value, context):
    # PyYAML also parses unquoted YYYY-MM-DD values as date objects.
    text = value.isoformat() if type(value) is date else value
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError(f"{context}: expected YYYY-MM-DD")
    return date.fromisoformat(text)


def validate_records(stores, visits):
    """Raise ValueError on invalid local configuration; never change records."""
    if not isinstance(stores, list) or not isinstance(visits, list):
        raise ValueError("instances must be a list")
    by_id = {}
    for record in stores:
        if not isinstance(record, dict) or record.get("class") != "Store":
            raise ValueError("store registry contains a non-Store record")
        store_id = _required_text(record, "id", "Store")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", store_id) or store_id in by_id:
            raise ValueError(f"invalid or duplicate Store ID: {store_id}")
        data = record.get("data")
        if not isinstance(data, dict):
            raise ValueError(f"{store_id}: data must be an object")
        for key in ("name", "location"):
            _required_text(data, key, store_id)
        if data.get("operationType", "fixed_store") not in ("fixed_store", "mobile_team"):
            raise ValueError(f"{store_id}: invalid operationType")
        if "setupStatus" in data and data["setupStatus"] not in ("setup_pending", "ready"):
            raise ValueError(f"{store_id}: invalid setupStatus")
        for key in ("seacodeStoreId", "casStoreId"):
            if key in data and not re.fullmatch(r"[a-z][a-z0-9_]*", _required_text(data, key, store_id)):
                raise ValueError(f"{store_id}: invalid {key}")
        by_id[store_id] = data

    for key in ("seacodeStoreId", "casStoreId"):
        # Legacy Store records implicitly use their own ID in SeaCode.
        # Include those occupied app IDs even without explicit mapping fields.
        mapped = [
            data.get(key, store_id)
            for store_id, data in by_id.items()
            if key == "seacodeStoreId" or key in data
        ]
        if len(mapped) != len(set(mapped)):
            raise ValueError(f"duplicate {key} assignment")

    visit_ids = set()
    periods = {}
    for record in visits:
        if not isinstance(record, dict) or record.get("class") != "StoreVisit":
            raise ValueError("visit registry contains a non-StoreVisit record")
        visit_id = _required_text(record, "id", "StoreVisit")
        if visit_id in visit_ids:
            raise ValueError(f"duplicate StoreVisit ID: {visit_id}")
        visit_ids.add(visit_id)
        data, relations = record.get("data"), record.get("relations")
        if not isinstance(data, dict) or not isinstance(relations, dict):
            raise ValueError(f"{visit_id}: data and relations must be objects")
        _required_text(data, "location", visit_id)
        team = relations.get("atStore")
        if not isinstance(team, str) or team not in by_id or by_id[team].get("operationType") != "mobile_team":
            raise ValueError(f"{visit_id}: atStore must reference a mobile_team")
        host = relations.get("hostStore")
        if host is not None and (not isinstance(host, str) or host not in by_id or host == team):
            raise ValueError(f"{visit_id}: hostStore must reference a different registered Store")
        start = _day(data.get("startDate"), visit_id)
        end = date.max if data.get("endDate") is None else _day(data["endDate"], visit_id)
        if end < start:
            raise ValueError(f"{visit_id}: endDate is before startDate")
        periods.setdefault(team, []).append((start, end, visit_id))

    for team, entries in periods.items():
        entries.sort()
        for previous, current in zip(entries, entries[1:]):
            if current[0] <= previous[1]:
                raise ValueError(f"{team}: overlapping StoreVisit dates ({previous[2]}, {current[2]})")


def _load_instances(path):
    with path.open(encoding="utf-8") as source:
        document = yaml.safe_load(source)
    if not isinstance(document, dict) or not isinstance(document.get("instances"), list):
        raise ValueError(f"{path.name}: instances must be a list")
    return document["instances"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        stores = _load_instances(args.root / "instances/master/stores.yaml")
        visits = []
        for path in sorted((args.root / "instances/store_visits").glob("*.yaml")):
            visits.extend(_load_instances(path))
        validate_records(stores, visits)
    except (OSError, ValueError, yaml.YAMLError) as error:
        parser.exit(1, f"FAIL: {error}\n")
    print(f"PASS: {len(stores)} stores, {len(visits)} visits (local configuration only; live connections not checked)")


if __name__ == "__main__":
    main()
