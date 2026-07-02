#!/usr/bin/env python3
"""워터비 데이터 검증 스크립트.

schema.yaml의 필드 정의와 제약조건을 기준으로 instances/ 아래
모든 YAML 데이터를 기계 검증한다.

검사 항목:
  - YAML 파싱 및 레코드 형태 (id / class / data)
  - 레코드 ID 전역 유일성
  - 관계 참조 무결성 (모든 관계 ID가 실제 존재하는지)
  - 필수 필드 존재 여부 (schema.yaml required 기준)
  - 날짜 형식 (YYYY-MM-DD)
  - 클래스별 비즈니스 제약 (schema.yaml constraints 참조)

사용법:
  python3 scripts/validate.py          # 전체 검증, 오류 시 exit 1
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

DAY_KEYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
PLAN_STATUS = {"planned", "in_progress", "completed"}
STAFF_ROLES = {"팀장", "직원"}
SCHEDULE_TYPES = {"근무", "발주", "생산", "기타"}
PSPEC_CATEGORIES = {"재료", "포장재", "소모품"}
DATE_FIELDS = {"date", "endDate", "effectiveFrom", "effectiveTo", "weekStart"}

# 파일 경로에서 매장 추론 (매장별 분할 파일)
STORE_FILES = {
    "wangsimni": "store_wangsimni",
    "mapo": "store_mapo",
    "wolgye": "store_wolgye",
}

errors = []
warnings = []


def err(path, rec_id, msg):
    errors.append(f"{path}: [{rec_id}] {msg}")


def warn(path, rec_id, msg):
    warnings.append(f"{path}: [{rec_id}] {msg}")


def is_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def load_schema():
    with (ROOT / "schema.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def store_from_path(path):
    return STORE_FILES.get(path.stem)


def collect_records():
    """instances/ 아래 모든 YAML을 읽어 (path, record) 목록을 만든다."""
    records = []
    for path in sorted((ROOT / "instances").rglob("*.yaml")):
        rel = path.relative_to(ROOT)
        try:
            with path.open(encoding="utf-8") as f:
                doc = yaml.safe_load(f)
        except yaml.YAMLError as e:
            err(rel, "-", f"YAML 파싱 실패: {e}")
            continue
        if doc is None:
            continue
        if not isinstance(doc, dict) or "instances" not in doc:
            err(rel, "-", "최상위에 instances: 키가 없음")
            continue
        items = doc["instances"] or []
        if not isinstance(items, list):
            err(rel, "-", "instances가 리스트가 아님")
            continue
        for rec in items:
            if not isinstance(rec, dict):
                err(rel, "-", f"레코드가 매핑이 아님: {rec!r}")
                continue
            records.append((rel, path, rec))
    return records


def check_shape(records, schema):
    known_classes = set(schema.get("classes", {}))
    ids = {}
    for rel, _path, rec in records:
        rec_id = rec.get("id")
        if not rec_id:
            err(rel, "-", "id 누락")
            continue
        if rec_id in ids:
            err(rel, rec_id, f"ID 중복 (최초 등장: {ids[rec_id]})")
        else:
            ids[rec_id] = rel
        cls = rec.get("class")
        if not cls:
            err(rel, rec_id, "class 누락")
        elif cls not in known_classes:
            err(rel, rec_id, f"schema에 없는 class: {cls}")
        if not isinstance(rec.get("data"), dict):
            err(rel, rec_id, "data 누락 또는 매핑이 아님")
    return set(ids)


def check_fields(records, schema):
    classes = schema.get("classes", {})
    for rel, _path, rec in records:
        rec_id = rec.get("id", "-")
        cls_def = classes.get(rec.get("class"))
        if not cls_def or not isinstance(rec.get("data"), dict):
            continue
        data = rec["data"]
        props = cls_def.get("properties", {})
        for prop, spec in props.items():
            if spec.get("required") and data.get(prop) is None:
                err(rel, rec_id, f"필수 필드 누락: {prop}")
        for key in data:
            if key not in props:
                warn(rel, rec_id, f"schema에 없는 필드: {key}")
        for key, value in data.items():
            if key in DATE_FIELDS and value is not None and not is_date(value):
                err(rel, rec_id, f"{key} 날짜 형식 오류: {value!r}")


def check_relations(records, schema, all_ids):
    classes = schema.get("classes", {})
    for rel, _path, rec in records:
        rec_id = rec.get("id", "-")
        cls = rec.get("class")
        cls_def = classes.get(cls)
        if not cls_def:
            continue
        rel_defs = cls_def.get("relations", {}) or {}
        relations = rec.get("relations") or {}
        if not isinstance(relations, dict):
            err(rel, rec_id, "relations가 매핑이 아님")
            continue

        for key, value in relations.items():
            if key not in rel_defs:
                warn(rel, rec_id, f"schema에 없는 관계: {key}")
                continue
            if key in ("uses", "packaging"):
                continue  # 아래에서 별도 검사
            if value is None:
                if not rel_defs[key].get("nullable"):
                    err(rel, rec_id, f"관계 {key}가 null (nullable 아님)")
                continue
            if value not in all_ids:
                err(rel, rec_id, f"관계 {key} → 존재하지 않는 ID: {value}")

        for key, spec in rel_defs.items():
            if key in ("uses", "packaging"):
                continue
            if not spec.get("nullable") and relations.get(key) is None:
                err(rel, rec_id, f"필수 관계 누락: {key}")

        # Recipe.uses / Recipe.packaging
        for entry in relations.get("uses") or []:
            ing = entry.get("ingredient")
            if not ing:
                err(rel, rec_id, "uses 항목에 ingredient 누락")
            elif ing not in all_ids:
                err(rel, rec_id, f"uses → 존재하지 않는 재료: {ing}")
            if entry.get("amount") is None:
                warn(rel, rec_id, f"uses[{ing}] amount 미입력 (미계량 레시피)")
            if not entry.get("unit"):
                err(rel, rec_id, f"uses[{ing}] unit 누락")
            pspec = entry.get("pspec")
            if pspec and pspec not in all_ids:
                err(rel, rec_id, f"uses[{ing}] → 존재하지 않는 pspec: {pspec}")
        for entry in relations.get("packaging") or []:
            pspec = entry.get("pspec")
            if not pspec:
                err(rel, rec_id, "packaging 항목에 pspec 누락")
            elif pspec not in all_ids:
                err(rel, rec_id, f"packaging → 존재하지 않는 pspec: {pspec}")


def check_business_rules(records):
    telegram_ids = {}
    active_recipes = {}   # (store, product) → rec_id (effectiveTo null)
    active_templates = {}  # (store, product) → rec_id
    plan_keys = {}        # (store, product, weekStart) → rec_id

    for rel, path, rec in records:
        rec_id = rec.get("id", "-")
        cls = rec.get("class")
        data = rec.get("data") or {}
        relations = rec.get("relations") or {}
        file_store = store_from_path(path)

        if cls == "SalesRecord":
            qty, price, total = data.get("qty"), data.get("unitPrice"), data.get("totalAmount")
            if None not in (qty, price, total) and qty * price != total:
                err(rel, rec_id, f"totalAmount({total}) ≠ qty×unitPrice({qty * price})")

        elif cls == "Staff":
            tid = data.get("telegramId")
            if tid is not None:
                if not isinstance(tid, str):
                    err(rel, rec_id, "telegramId는 문자열이어야 함 (따옴표 필요)")
                if tid in telegram_ids:
                    err(rel, rec_id, f"telegramId 중복: {telegram_ids[tid]}")
                telegram_ids[tid] = rec_id
            role = data.get("role")
            if role not in STAFF_ROLES:
                err(rel, rec_id, f"role은 팀장/직원 중 하나: {role!r}")
            if role == "직원" and relations.get("atStore") is None:
                err(rel, rec_id, "직원은 atStore 필수")
            if role == "팀장" and relations.get("atStore") is not None:
                err(rel, rec_id, "팀장은 atStore가 null이어야 함")

        elif cls == "Recipe":
            key = (file_store, relations.get("forProduct"))
            if data.get("effectiveTo") is None:
                if key in active_recipes:
                    err(rel, rec_id,
                        f"같은 (매장, 상품)에 활성 레시피 중복: {active_recipes[key]}")
                else:
                    active_recipes[key] = rec_id

        elif cls == "ProductionTemplate":
            key = (relations.get("atStore"), relations.get("forProduct"))
            if data.get("effectiveTo") is None:
                if key in active_templates:
                    err(rel, rec_id,
                        f"같은 (매장, 상품)에 활성 템플릿 중복: {active_templates[key]}")
                else:
                    active_templates[key] = rec_id
            _check_daily(rel, rec_id, data.get("dailyQty"), "dailyQty")
            ef, et = data.get("effectiveFrom"), data.get("effectiveTo")
            if ef and et and is_date(ef) and is_date(et) and et < ef:
                err(rel, rec_id, f"effectiveTo({et})가 effectiveFrom({ef})보다 이전")

        elif cls == "ProductionPlan":
            ws = data.get("weekStart")
            if is_date(ws) and date.fromisoformat(ws).weekday() != 0:
                err(rel, rec_id, f"weekStart가 월요일이 아님: {ws}")
            if data.get("status") not in PLAN_STATUS:
                err(rel, rec_id, f"status 오류: {data.get('status')!r}")
            key = (relations.get("atStore"), relations.get("forProduct"), ws)
            if key in plan_keys:
                err(rel, rec_id, f"(매장, 상품, weekStart) 중복: {plan_keys[key]}")
            else:
                plan_keys[key] = rec_id
            for field in ("dailyPlan", "dailyAdjusted", "dailyActual"):
                _check_daily(rel, rec_id, data.get(field), field)

        elif cls == "Ingredient":
            for field in ("thawLossRate", "trimLossRate"):
                v = data.get(field)
                if v is not None and not (0 <= v < 100):
                    err(rel, rec_id, f"{field}는 0 이상 100 미만: {v}")

        elif cls == "PurchaseSpec":
            cat = data.get("category")
            if cat not in PSPEC_CATEGORIES:
                err(rel, rec_id, f"category는 재료/포장재/소모품 중 하나: {cat!r}")
            cpk = data.get("countPerKg")
            if cpk is not None and cpk <= 0:
                err(rel, rec_id, f"countPerKg는 양수: {cpk}")

        elif cls == "PriceHistory":
            up = data.get("unitPrice")
            if up is not None and up <= 0:
                err(rel, rec_id, f"unitPrice는 양수: {up}")

        elif cls == "Schedule":
            if data.get("type") not in SCHEDULE_TYPES:
                err(rel, rec_id, f"type은 근무/발주/생산/기타 중 하나: {data.get('type')!r}")
            d, ed = data.get("date"), data.get("endDate")
            if d and ed and is_date(d) and is_date(ed) and ed < d:
                err(rel, rec_id, f"endDate({ed})가 date({d})보다 이전")

        elif cls == "InboundRecord":
            q = data.get("quantity")
            if q is not None and q <= 0:
                err(rel, rec_id, f"quantity는 양수: {q}")


def _check_daily(rel, rec_id, obj, field):
    if obj is None:
        return
    if not isinstance(obj, dict):
        err(rel, rec_id, f"{field}가 매핑이 아님")
        return
    bad_keys = set(obj) - DAY_KEYS
    if bad_keys:
        err(rel, rec_id, f"{field}에 잘못된 요일 키: {sorted(bad_keys)}")
    for k, v in obj.items():
        if not isinstance(v, (int, float)) or v < 0:
            err(rel, rec_id, f"{field}.{k}는 0 이상의 숫자: {v!r}")


def main():
    schema = load_schema()
    records = collect_records()
    all_ids = check_shape(records, schema)
    check_fields(records, schema)
    check_relations(records, schema, all_ids)
    check_business_rules(records)

    print(f"검사한 레코드: {len(records)}개")
    if warnings:
        print(f"\n경고 {len(warnings)}건:")
        for w in warnings:
            print(f"  ⚠ {w}")
    if errors:
        print(f"\n오류 {len(errors)}건:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("\n오류 없음 ✓")


if __name__ == "__main__":
    main()
