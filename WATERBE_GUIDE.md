# 워터비(WATERBE) 운영 가이드

워터비 비즈니스 규칙, 파일 위치, ID 규칙을 기술한다.

> **필드·관계 정의는 `schema.yaml`이 단일 소스다.** 이 문서에는 필드 표를 두지 않는다.
> 데이터 수정 후에는 `python3 scripts/validate.py`로 검증한다.

---

## 워터비란?

이마트 수산물 코너에 입점한 밀키트·단품 판매 사업. 현재 3개 매장 운영.

| 매장 | ID | 약어 | 기본 납품업체 |
|------|----|------|--------------|
| 왕십리점 | store_wangsimni | ws | 남선푸드 |
| 마포점 | store_mapo | mp | 남선푸드 |
| 월계점 | store_wolgye | wg | 대영상사 |

---

## 파일 구조

```
waterbe/
├── schema.yaml              # 스키마 정의 (클래스·속성·관계·제약) — 단일 소스
├── WATERBE_GUIDE.md         # 이 문서 (비즈니스 규칙)
├── PERSONNEL_GUIDE.md       # 인사관리 가이드
├── AGENTS.md                # 에이전트 작업 규칙
├── scripts/
│   ├── validate.py          # 데이터 검증 (참조 무결성·제약조건)
│   ├── calc_order.py        # 발주량 계산
│   ├── namseon_sales.py     # 남선매출 SQLite 조회
│   ├── namseon_drive_sync.py / namseon_sync_now.sh  # Drive 동기화
│   ├── sync_to_supabase.py
│   └── export_github_data.py
└── instances/
    ├── master/              # 읽기 전용 기준 데이터
    │   ├── stores.yaml
    │   ├── categories.yaml
    │   ├── products.yaml
    │   ├── ingredients.yaml
    │   ├── purchase_specs.yaml
    │   ├── price_history.yaml
    │   └── recipes/{wangsimni,mapo,wolgye}.yaml
    ├── staff.yaml
    ├── schedules.yaml
    ├── inventory/{매장}.yaml            # 재고실사
    │   └── inbound/{매장}.yaml          # 입고기록
    ├── production/{매장}.yaml           # 주간 생산계획
    │   └── templates/{매장}.yaml        # 요일별 기본생산수량
    └── sales/
        ├── {매장}.yaml                  # 수기 매출 (현재 미사용)
        └── namseon/                     # 남선매출 SQLite 작업 공간
```

모든 데이터 파일은 최상위 `instances:` 아래 `id / class / data / relations` 형태의 레코드 목록이다.
매장별 분할 파일(recipes, inventory, production, sales)에서는 **파일 이름이 매장을 결정한다.**

---

## 데이터 흐름

```
Store (매장)
  │   Product (상품) ←─ forProduct ── Recipe (레시피, 매장별 파일)
  │                                      └─ uses ──→ Ingredient (재료)
  │                                                     └─ forIngredient ←── PurchaseSpec (발주규격)
  │                                                                              └─ forPurchaseSpec ←── PriceHistory (가격이력)
  ├─ atStore ←── InventorySnapshot (재고실사) / InboundRecord (입고기록)
  ├─ atStore ←── ProductionTemplate (기본생산수량) → ProductionPlan (생산계획)
  └─ atStore ←── SalesRecord (매출기록)
```

1. **상품은 매장별로 고유하다** — 각 매장의 레시피가 곧 그 매장의 상품이며, 이름이 같아도 매장이 다르면 별개 Product다. Product는 레시피 버전이 바뀌어도 변하지 않는 앵커 역할(생산·매출이 참조). 매장 취급 여부는 해당 매장 레시피 파일의 존재로 판단한다.
   - 이마트 상품코드(martCode)는 전 매장 공통 카탈로그를 각 매장이 개별적으로 가져다 쓰는 것이므로 상품 식별자가 아니다 — Recipe에 기록한다.
2. 레시피는 **재료**를 사용량과 함께 참조한다
3. 재료는 **발주규격**으로 주문한다 → 규격마다 날짜별 **가격이력**이 쌓인다 (납품업체는 PriceHistory.vendor 문자열)
4. 매장별 **기본생산수량** 템플릿 → 주간 **생산계획** 생성
5. 주기적으로 **재고실사** 기록, 입고 시 **입고기록** 추가
6. 매출은 남선매출 SQLite(`instances/sales/README.md` 참조)로 조회한다. 매장별 수기 매출 YAML은 현재 사용하지 않는다.

---

## ID 명명 규칙

| 클래스 | 접두사 | 예시 |
|--------|--------|------|
| Store | `store_` | `store_wangsimni` |
| Category | `cat_` | `cat_mealkit` |
| Product | `prod_{매장약어}_{상품명}` | `prod_ws_문어전복해물탕` |
| Ingredient | `ing_` + 재료명 | `ing_낙지`, `ing_흰다리새우살_L_페루` |
| Recipe | `recipe_{매장약어}_{상품명}` (개정판은 `_2`, `_3` …) | `recipe_ws_문어전복해물탕` |
| PurchaseSpec | `pspec_` + 순번 | `pspec_001` |
| PriceHistory | `ph_` + 순번 | `ph_001` |
| ProductionTemplate | `tmpl_{매장약어}_{상품명}` (개정판은 `_2` …) | `tmpl_wg_문어전복해물탕` |
| ProductionPlan | `plan_{매장약어}_{YYYYMMDD}_{상품명}` | `plan_ws_20260407_문어전복해물탕` |
| InventorySnapshot | `snap_{매장약어}_{YYYYMMDD}_{재료약어}` | `snap_wg_20260414_낙지` |
| InboundRecord | `inbound_{매장약어}_{YYYYMMDD}_{순번}` | `inbound_ws_20260407_1` |
| SalesRecord | `sale_{매장약어}_{YYYYMMDD}_{상품명}` | `sale_ws_20260315_문어전복해물탕` |

**상품명 표기 규칙**: 상품 이름에서 공백을 제거하고, 괄호는 `_`로 바꾼다.
예: `손질 흰다리새우살(대)` → `손질흰다리새우살_대`. 밀키트/단품/게장 구분은 ID가 아니라 Category로 관리한다.
| Staff | `staff_` + 순번 | `staff_001` |
| Schedule | `sched_` + 이름 | `sched_order_wolgye` |

**Ingredient ID 분리 기준**
- 기본형: `ing_{재료명}` — 원산지·성분 구분 불필요
- 크기·등급 다름: `ing_{재료명}_{L|S}_{원산지}` (예: `ing_흰다리새우살_L_페루`)
- 원산지만 다름: 원산지 suffix (예: `ing_게_바레인`)
- 성분·알레르기가 다르면 → ID 분리 / 납품업체만 다르면 → 같은 ID

---

## 비즈니스 규칙

### 납품업체(vendor) 우선순위
원가 계산 시 매장 기본 vendor 단가를 우선 적용.
기본 vendor 가격이 없을 경우에만 다른 vendor 가격 사용.
(매장별 기본 vendor는 상단 매장 표 참조)

### 대영상사 배송비
대영상사 품목은 price_history의 unitPrice에 배송비가 포함되지 않는다.
원가 계산 시 아래 배송비를 박스(발주단위)당 가산.

| 품목 | 박스당 배송비 |
|------|------------|
| 전복 | 5,000원 |
| 그 외 | 3,000원 |

### 양배추콩나물세트
레시피에 `ing_양배추 1팩` + `ing_콩나물 1팩`이 함께 등장하면
실제로는 `pspec_086` (양배추콩나물세트) 1팩으로 처리.
개별 원가를 합산하지 않는다.

### 원가 계산 공식
```
실수율 = (1 − thawLossRate/100) × (1 − trimLossRate/100)   # null은 0으로

발주단위 g = orderUnit에서 환산 (예: "9kg" → 9000g. scripts/calc_order.py가 파싱)

원가/g  = (unitPrice + deliveryFee) ÷ 발주단위g ÷ 실수율

개수 기준 재료 (countPerKg 있는 경우):
  1개 무게(g) = 1000 ÷ countPerKg
  1개 원가    = 원가/g × 1개 무게

레시피 1팩 원가 = Σ(재료별 원가) + Σ(포장재별 원가)
```

### 수수료 구조
- **이마트 수수료**: 21.5% (판매가 기준)
- **남선푸드 수수료**: 5% (판매가 기준)
- **실수령** = 판매가 × (1 - 0.215 - 0.05) = 판매가 × 0.735

### 할인 판매 마진 계산
```
할인 판매가 = 정가 × (1 - 할인율)
이마트 수수료 = 할인 판매가 × 0.215
남선푸드 수수료 = 할인 판매가 × 0.05
실수령 = 할인 판매가 - 이마트 수수료 - 남선푸드 수수료
마진 = 실수령 - 원가(재료+포장)
```

예) 프리미엄 낙곱새 왕십리 40% 할인 시:
- 정가 25,800원 → 할인가 15,480원
- 이마트 -3,328원 / 남선푸드 -774원 → 실수령 11,378원
- 원가 8,054원 → **마진 3,324원**

### 적정원가 기준
```
적정원가 = 판매가 × 0.735 × 0.75  (= 판매가 × 55.1%)
```
실수령(73.5%)의 75%를 원가 한도로 본다.

---

## 데이터 무결성 규칙

전체 제약조건 목록은 `schema.yaml`의 `constraints:` 절이 소유하며,
`python3 scripts/validate.py`가 기계 검증한다. 핵심 원칙:

- **이력 보존(append-only)**: PriceHistory · InventorySnapshot · InboundRecord는 덮어쓰기 금지, 항상 새 레코드 추가
- **버전 관리**: Recipe · ProductionTemplate 변경 시 기존 레코드의 effectiveTo를 전날로 채우고 새 레코드 추가. 현재 적용분 = effectiveTo가 null인 레코드 (조합당 최대 1개)
- **계획 고정**: ProductionPlan.dailyPlan은 수정 금지 — 조정은 dailyAdjusted, 실적은 dailyActual에
- **참조 무결성**: 모든 관계 ID는 실제 존재하는 레코드를 가리켜야 하며, 레코드 ID는 전역 유일
