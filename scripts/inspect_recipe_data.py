"""Read-only recipe/purchase-price inventory and reference checks (requires PyYAML)."""
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def inspect(root=ROOT):
    base = root / "instances/master"
    files = [base / (name + ".yaml") for name in
             ("stores", "products", "ingredients", "purchase_specs", "price_history")]
    files += sorted((base / "recipes").glob("*.yaml"))
    records, counts, issues = {}, {}, []
    for path in files:
        rows = yaml.safe_load(path.read_text(encoding="utf-8"))["instances"] or []
        counts[str(path.relative_to(root))] = len(rows)
        for row in rows:
            if row["id"] in records:
                issues.append({"id": row["id"], "issue": "duplicate_id"})
            records[row["id"]] = row
    refs = {"forProduct": "Product", "atStore": "Store",
            "forIngredient": "Ingredient", "forPurchaseSpec": "PurchaseSpec"}
    for row in records.values():
        rel = row.get("relations") or {}
        for field, expected in refs.items():
            target = rel.get(field)
            if target and (target not in records or records[target]["class"] != expected):
                issues.append({"id": row["id"], "issue": "invalid_reference", "field": field, "target": target})
        if row["class"] != "Recipe":
            continue
        if not rel.get("atStore"):
            issues.append({"id": row["id"], "issue": "missing_store_reference"})
        for use in rel.get("uses") or []:
            for field, expected in (("ingredient", "Ingredient"), ("pspec", "PurchaseSpec")):
                target = use.get(field)
                if not target or target not in records or records[target]["class"] != expected:
                    issues.append({"id": row["id"], "issue": "invalid_use_reference", "field": field, "target": target})
            if use.get("amount") is None or not use.get("unit"):
                issues.append({"id": row["id"], "issue": "incomplete_quantity", "ingredient": use.get("ingredient")})
            spec = records.get(use.get("pspec"), {})
            ingredient = (spec.get("relations") or {}).get("forIngredient")
            if ingredient and ingredient != use.get("ingredient"):
                issues.append({"id": row["id"], "issue": "spec_ingredient_mismatch", "pspec": use.get("pspec")})
    priced = {(r.get("relations") or {}).get("forPurchaseSpec") for r in records.values() if r["class"] == "PriceHistory"}
    missing_prices = [r["id"] for r in records.values() if r["class"] == "PurchaseSpec" and r["id"] not in priced]
    return {"counts": counts, "issues": issues, "specs_without_price_history": missing_prices,
            "warning": "Inventory of saved records only; no current price or complete cost calculation asserted."}


if __name__ == "__main__":
    print(json.dumps(inspect(), ensure_ascii=False, indent=2))
