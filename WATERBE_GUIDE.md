# 워터비(WATERBE) 온톨로지 가이드

워터비 데이터 구조, 클래스 정의, 파일 위치, ID 규칙, 비즈니스 규칙을 기술한다.

---

## 워터비란?

이마트 수산물 코너에 입점한 밀키트·단품 판매 사업. 현재 3개 매장 운영.

| 매장 | ID | 기본 납품업체 |
|------|----|--------------|
| 왕십리점 | store_wangsimni | 남선푸드 |
| 마포점 | store_mapo | 남선푸드 |
| 월계점 | store_wolgye | 대영상사 |

---

## 파일 구조

```
waterbe/
├── schema.yaml              # 스키마 정의 (클래스·속성·관계)
├── WATERBE_GUIDE.md         # 이 문서
├── PERSONNEL_GUIDE.md       # 인사관리 가이드
├── CHANGE_REQUESTS.md       # 변경 요청 기록
└── instances/
    ├── master/              # 읽기 전용 기준 데이터
    │   ├── stores.yaml
    │   ├── categories.yaml
    │   ├── products.yaml
    │   ├── ingredients.yaml
    │   ├── purchase_specs.yaml
    │   ├── price_history.yaml
    │   └── recipes/
    │       ├── wangsimni.yaml
    │       ├── mapo.yaml
    │       └── wolgye.yaml
    │
    ├── staff.yaml
    ├── schedules.yaml
    ├── inventory/
    │   ├── wangsimni.yaml
    │   ├── mapo.yaml
    │   ├── wolgye.yaml
    │   └── inbound/
    │       ├── wangsimni.yaml
    │       ├── mapo.yaml
    │       └── wolgye.yaml
    ├── production/
    │   ├── wangsimni.yaml
    │   ├── mapo.yaml
    │   ├── wolgye.yaml
    │   └── templates/
    │       ├── wangsimni.yaml
    │       ├── mapo.yaml
    │       └── wolgye.yaml
    └── sales/
        ├── wangsimni.yaml
        ├── mapo.yaml
        └── wolgye.yaml
```

---

## 클래스 정의

### Store (매장) — `master/stores.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| name | string | 매장명 |
| location | string | 위치 |
| branch | string | 이마트 지점명 |

### Category (카테고리) — `master/categories.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| name | string | 카테고리명 |
| displayOrder | number | 표시 순서 |
| subClassOf | → Category | 상위 카테고리 (최상위는 null) |

### Product (상품) — `master/products.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| name | string | 상품명 |
| unit | string | 판매 단위 (1팩, 100g 등) |
| price | number\|null | 판매가격 (원). 미정이면 null |
| belongsTo | → Category | 카테고리 |
| soldAt | → Store[] | 판매 매장 목록 |

### Ingredient (재료) — `master/ingredients.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| name | string | 재료명 |
| defaultUnit | string | 기본 단위 (g, 개 등) |
| ingredientType | string | 재료 분류 (1차수산물, 채소, 소스 등) |
| composition | string | 성분 표기 |
| origin | string | 원산지 |
| allergen | string | 알레르기 유발물질 |
| thawLossRate | number | 해동 손실률 (%, null=0%) |
| trimLossRate | number | 손질 손실률 (%, null=0%) |

> 실수율(%) = (1 − thawLossRate/100) × (1 − trimLossRate/100)

### PurchaseSpec (발주규격) — `master/purchase_specs.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| orderName | string | 발주명 (납품업체 기준 상품명) |
| orderUnit | string | 발주단위 (9kg, 1박스 등) |
| unitG | number | 발주단위의 그램 환산값 (9kg → 9000) |
| category | string | 재료 / 포장재 / 소모품 |
| countPerKg | number | 미수 (개/kg). 새우·전복 등 개수 기준 재료만 입력 |
| packCount | number | 팩 단위 재료의 1박스당 팩 수 |
| packUnitPrice | number | 1팩당 단가 (팩 단위 재료 전용) |
| forIngredient | → Ingredient | 해당 재료 (포장재·소모품은 null) |

> `countPerKg`가 있는 재료: 1개 무게(g) = 1000 ÷ countPerKg

### PriceHistory (가격이력) — `master/price_history.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| unitPrice | number | 발주단위 기준 총금액 (원) |
| date | string | 가격 기준일자 (YYYY-MM-DD) |
| vendor | string | 납품업체 (남선푸드 / 대영상사) |
| deliveryFee | number | 박스당 배송비 (원). 별도 청구되는 경우만 입력 |
| memo | string | 가격 변동 사유 등 |
| forPurchaseSpec | → PurchaseSpec | 해당 발주규격 |

> 현재 단가 = 해당 pspec의 레코드 중 date 기준 최신 레코드.
> 가격 변경 시 기존 레코드 수정 금지 — 새 레코드 추가.

### Recipe (레시피) — `master/recipes/{매장}.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| name | string | 레시피명 |
| forProduct | → Product | 대상 상품 |
| atStore | → Store | 해당 매장 |
| uses[].ingredient | → Ingredient | 사용 재료 |
| uses[].amount | number | 사용량 |
| uses[].unit | string | 단위 (g, 마리, 팩 등) |
| packaging[].pspec | → PurchaseSpec | 사용 포장재 |
| packaging[].quantity | number | 수량 |

> (forProduct, atStore) 조합은 유일 — 같은 매장·상품 중복 불가.

### ProductionTemplate (기본생산수량) — `production/templates/{매장}.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| dailyQty | object | 요일별 기본 생산량 {mon/tue/wed/thu/fri/sat/sun: n}. 미생산=0 |
| unit | string | 생산량 단위 (개 / kg) |
| effectiveFrom | string | 적용 시작일 (YYYY-MM-DD) |
| effectiveTo | string\|null | 적용 종료일. **null = 현재 적용 중** |
| memo | string | 변경 사유 등 |
| forProduct | → Product | 대상 상품 |
| atStore | → Store | 해당 매장 |

> 변경 시: 기존 레코드의 effectiveTo를 전날로 채우고 새 레코드 추가 (덮어쓰기 금지).
> 현재 적용 중인 템플릿 = effectiveTo가 null인 레코드.

### ProductionPlan (생산계획) — `production/{매장}.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| weekStart | string | 주 시작일 (YYYY-MM-DD, 월요일) |
| dailyPlan | object | 요일별 계획 수량 (템플릿 dailyQty 복사) |
| dailyAdjusted | object\|null | 요일별 조정 수량. 조정된 요일만 입력 |
| dailyActual | object\|null | 요일별 실제 생산량. 완료 후 입력 |
| status | string | planned / in_progress / completed |
| forProduct | → Product | 대상 상품 |
| atStore | → Store | 해당 매장 |

> (forProduct, atStore, weekStart) 조합은 유일.
> dailyPlan은 수정 금지 — 조정은 dailyAdjusted에만.
> 유효 생산량: dailyAdjusted[day] 있으면 우선, 없으면 dailyPlan[day].

### InventorySnapshot (재고실사) — `inventory/{매장}.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| date | string | 실사일자 (YYYY-MM-DD) |
| quantity | number | 실사 수량 |
| unit | string | 단위 (kg, 개 등) |
| memo | string | 메모 |
| forIngredient | → Ingredient | 해당 재료 |
| atStore | → Store | 해당 매장 |

> 실사할 때마다 새 레코드 추가 (덮어쓰기 금지).

### InboundRecord (입고기록) — `inventory/inbound/{매장}.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| date | string | 입고일자 (YYYY-MM-DD) |
| quantity | number | 입고 수량 (발주단위 기준) |
| unit | string | 단위 (박스, kg 등) |
| memo | string | 업체명, 특이사항 등 |
| forPurchaseSpec | → PurchaseSpec | 해당 발주규격 |
| atStore | → Store | 입고 매장 |

> 입고 시마다 새 레코드 추가 (덮어쓰기 금지).

### SalesRecord (매출기록) — `sales/{매장}.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| date | string | 판매일자 (YYYY-MM-DD) |
| qty | number | 판매 수량 |
| unitPrice | number | 판매 단가 (원) |
| totalAmount | number | 총 매출액 (qty × unitPrice) |
| forProduct | → Product | 판매 상품 |
| atStore | → Store | 해당 매장 |

### Staff (직원) — `staff.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| name | string | 이름 |
| telegramId | string | 텔레그램 사용자 ID (숫자 문자열, 유일) |
| role | string | 팀장 / 직원 |
| atStore | → Store\|null | 소속 매장 (직원만. 팀장은 null) |

### Schedule (일정) — `schedules.yaml`
| 필드 | 타입 | 설명 |
|------|------|------|
| date | string | 일자 (YYYY-MM-DD) |
| endDate | string\|null | 종료일 (하루짜리면 null) |
| type | string | 근무 / 발주 / 생산 / 기타 |
| title | string | 제목 |
| description | string | 상세 내용 |
| assignee | string | 담당자 |
| atStore | → Store | 해당 매장 |

---

## 클래스 관계도

```
Store (매장)
  └─ carries ──→ Product (상품)
  │                 └─ forProduct ←── Recipe (레시피)
  │                 │                     └─ uses ──→ Ingredient (재료)
  │                 │                                     └─ forIngredient ←── PurchaseSpec (발주규격)
  │                 │                                                               └─ forPurchaseSpec ←── PriceHistory (가격이력)
  │                 ├─ forProduct ←── ProductionPlan (생산계획)
  │                 └─ forProduct ←── SalesRecord (매출기록)
  ├─ atStore ←── InventorySnapshot (재고실사)
  ├─ atStore ←── InboundRecord (입고기록)
  ├─ atStore ←── ProductionPlan (생산계획)
  ├─ atStore ←── ProductionTemplate (기본생산수량)
  └─ atStore ←── SalesRecord (매출기록)
```

**데이터 흐름**
1. 매장마다 판매하는 **상품**이 있다
2. 상품마다 매장별 **레시피**가 있다 (같은 상품도 매장마다 레시피가 다를 수 있음)
3. 레시피는 **재료**를 사용량과 함께 참조한다
4. 재료는 **발주규격**으로 주문한다 → 규격마다 날짜별 **가격이력**이 쌓인다
5. 매장별 **기본생산수량** 템플릿 → 주간 **생산계획** 생성
6. 주기적으로 **재고실사** 기록, 입고 시 **입고기록** 추가
7. 판매 후 **매출기록** 입력

---

## ID 명명 규칙

| 클래스 | 접두사 | 예시 |
|--------|--------|------|
| Store | `store_` | `store_wangsimni` |
| Category | `cat_` | `cat_mealkit` |
| Product (밀키트) | `prod_mk_` + 순번 | `prod_mk_001` |
| Product (단품) | `prod_sp_` + 순번 | `prod_sp_001` |
| Product (게장류) | `prod_gj_` + 순번 | `prod_gj_001` |
| Ingredient | `ing_` + 재료명 | `ing_낙지`, `ing_흰다리새우살_L_페루` |
| Recipe | `recipe_{매장}_{prod_id}` | `recipe_wangsimni_mk001` |
| PurchaseSpec | `pspec_` + 순번 | `pspec_001` |
| PriceHistory | `ph_` + 순번 | `ph_001` |
| ProductionTemplate | `tmpl_{매장약어}_{prod_id약어}_{YYYYMMDD}` | `tmpl_ws_mk001_20260402` |
| ProductionPlan | `plan_{매장약어}_{YYYYMMDD}_{prod_id약어}` | `plan_ws_20260407_mk001` |
| InventorySnapshot | `snap_{매장약어}_{YYYYMMDD}_{재료약어}` | `snap_ws_20260315_낙지` |
| InboundRecord | `inbound_{매장약어}_{YYYYMMDD}_{순번}` | `inbound_ws_20260407_1` |
| SalesRecord | `sale_{매장약어}_{YYYYMMDD}_{prod_id약어}` | `sale_ws_20260315_mk001` |

매장 약어: 왕십리=ws / 마포=mp / 월계=wg

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

| 매장 | 기본 vendor |
|------|------------|
| 왕십리 | 남선푸드 |
| 마포 | 남선푸드 |
| 월계 | 대영상사 |

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

원가/g  = (unitPrice + deliveryFee) ÷ unitG ÷ 실수율

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

- **PriceHistory**: 가격 변경 시 기존 레코드 수정 금지 → 새 레코드 추가
- **ProductionTemplate**: 변경 시 기존 레코드의 effectiveTo를 전날로 채우고 새 레코드 추가
- **ProductionPlan.dailyPlan**: 수정 금지 → 조정은 dailyAdjusted에만
- **InventorySnapshot**: 덮어쓰기 금지 → 실사할 때마다 새 레코드 추가
- **InboundRecord**: 덮어쓰기 금지 → 입고 시마다 새 레코드 추가
- **SalesRecord.totalAmount**: qty × unitPrice와 일치해야 함
- **Staff.telegramId**: 유일 (중복 등록 불가)
- **ProductionTemplate**: 같은 (forProduct, atStore) 조합에서 effectiveTo=null 레코드는 최대 1개
