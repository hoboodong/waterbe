# 워터비(WATERBE) 데이터 관리 가이드

> **에이전트에게**: 이 파일 하나만 읽으면 워터비 데이터를 즉시 사용할 수 있습니다.
> schema.yaml은 읽지 않아도 됩니다. 이 가이드에 필요한 모든 정보가 포함되어 있습니다.

---

## ⚠️ 반드시 지켜야 할 핵심 규칙

### 규칙 1: 단가 질문은 무조건 매입 단가로 처리
> "단가", "원가", "얼마야", "가격" 등 **재료명과 함께 오는 모든 질문**은 매입 단가 조회다.
> **products.yaml을 절대 보지 말 것.** products.yaml에는 소비자 판매가만 있다.

```
재료 단가 조회 순서 (반드시 이 순서로):
  1. ingredients.yaml → 재료 ID 확인
  2. purchase_specs.yaml → 해당 재료의 pspec 전체 검색
  3. price_history.yaml → 해당 pspec의 최신 레코드 → unitPrice
```

판매가를 묻는 경우만 products.yaml 조회:
- "판매가", "소비자가", "얼마에 팔아", "팔 때 가격" 등 명시적으로 판매 가격을 물을 때

### 규칙 2: "데이터 없음" 응답 금지
> price_history.yaml을 끝까지 스캔하기 전에 "데이터 없음", "정보 없음"이라고 답하지 말 것.
> 파일 전체를 검색했는데도 없을 때만 "단가 정보가 없습니다"라고 한다.

### 규칙 4: 양배추콩나물세트 원가 중복 계산 금지
> 레시피에 `ing_양배추 1팩` + `ing_콩나물 1팩`이 함께 등장하면,
> 실제로는 **양배추콩나물세트(pspec_086) 1팩(1,500원)** 하나다.
> 양배추와 콩나물 각각 원가를 계산하지 말고 pspec_086 단가 1,500원을 1회만 적용할 것.

### 규칙 3: 내부 ID 출력 금지
> ing_*, pspec_*, prod_* 등 내부 ID를 사용자에게 그대로 노출하지 말 것.
> 반드시 사람이 읽을 수 있는 이름으로 변환해서 출력한다.

---

## 워터비란?
이마트 수산물 코너에 입점한 밀키트·단품 판매 사업. 현재 3개 매장 운영.
- **왕십리점** (store_wangsimni)
- **마포점** (store_mapo)
- **월계점** (store_wolgye)

---

## 클래스별 핵심 필드

### Ingredient (재료) — `waterbe/instances/ingredients.yaml`
| 필드 | 설명 |
|------|------|
| name | 재료명 |
| defaultUnit | 기본 단위 (g, 개 등) |
| origin | 원산지 |
| composition | 성분 표기 |
| allergen | 알레르기 유발물질 |
| thawLossRate | 해동 손실률 (%, null=0%) |
| trimLossRate | 손질 손실률 (%, null=0%) |

### PurchaseSpec (발주규격) — `waterbe/instances/purchase_specs.yaml`
| 필드 | 설명 |
|------|------|
| orderName | 발주명 (납품업체 기준 상품명) |
| orderUnit | 발주단위 (예: 9kg, 1박스) |
| category | 재료 / 포장재 / 소모품 |
| countPerKg | 미수 (개/kg, 새우·전복 등 개수 기준 재료만) |
| forIngredient | 연결된 재료 ID |

### PriceHistory (가격이력) — `waterbe/instances/price_history.yaml`
| 필드 | 설명 |
|------|------|
| unitPrice | 발주단위 기준 총금액 (원) |
| date | 가격 기준일자 (YYYY-MM-DD) |
| vendor | 납품업체 (남선푸드 / 대영상사) |
| forPurchaseSpec | 연결된 발주규격 ID |

> **현재 단가** = 해당 pspec의 price_history 중 가장 최신 date 레코드

### Recipe (레시피) — `waterbe/instances/recipes/{매장}.yaml`
| 필드 | 설명 |
|------|------|
| forProduct | 대상 상품 ID |
| atStore | 해당 매장 ID |
| uses | 재료 목록 (ingredient, amount, unit) |
| packaging | 포장재 목록 (pspec, quantity, unit) |

### ProductionPlan (생산계획) — `waterbe/instances/production/{매장}.yaml`
| 필드 | 설명 |
|------|------|
| weekStart | 주 시작일 (YYYY-MM-DD, 월요일) |
| dailyPlan | 요일별 계획 수량 {mon/tue/wed/thu/fri/sat/sun: n} |
| dailyAdjusted | 조정 요일만 입력 (나머지는 dailyPlan 사용) |
| dailyActual | 실제 생산량 (완료 후 입력) |
| status | planned / in_progress / completed |

### InboundRecord (입고기록) — `waterbe/instances/inventory/inbound/{매장}.yaml`
| 필드 | 설명 |
|------|------|
| date | 입고일자 (YYYY-MM-DD) |
| quantity | 입고 수량 (발주단위 기준) |
| unit | 단위 |
| forPurchaseSpec | 연결된 발주규격 ID |
| atStore | 입고 매장 ID |

### InventorySnapshot (재고실사) — `waterbe/instances/inventory/{매장}.yaml`
| 필드 | 설명 |
|------|------|
| date | 실사일자 (YYYY-MM-DD) |
| quantity | 실사 수량 |
| unit | 단위 |
| forIngredient | 재료 ID |
| atStore | 매장 ID |

### SalesRecord (매출기록) — `waterbe/instances/sales/{매장}.yaml`
| 필드 | 설명 |
|------|------|
| date | 판매일자 (YYYY-MM-DD) |
| qty | 판매 수량 |
| unitPrice | 판매 단가 (원) |
| totalAmount | 총 매출액 (qty × unitPrice) |
| forProduct | 판매 상품 ID |
| atStore | 매장 ID |

---

## 역할
워터비 사업 데이터를 관리하는 에이전트.
`waterbe/instances/` 하위 파일의 실제 데이터를 조회·입력·수정한다.

## 파일 구조
```
waterbe/
├── schema.yaml          # 스키마 정의 (클래스·속성·관계)
├── WATERBE_GUIDE.md     # 이 문서
├── PERSONNEL_GUIDE.md   # 인사관리 에이전트 가이드
├── instances/
│   ├── stores.yaml          # 매장 인스턴스
│   ├── staff.yaml           # 직원 인스턴스 (텔레그램 ID·역할·매장)
│   ├── schedules.yaml       # 일정 인스턴스 (전 매장 통합)
│   ├── products.yaml        # 제품 인스턴스
│   ├── categories.yaml      # 카테고리 인스턴스
│   ├── ingredients.yaml     # 재료 인스턴스
│   ├── purchase_specs.yaml  # 발주규격 인스턴스
│   ├── price_history.yaml   # 가격이력 인스턴스
│   ├── recipes/             # 레시피 인스턴스 (매장별 분리)
│   │   ├── wangsimni.yaml
│   │   ├── mapo.yaml
│   │   └── wolgye.yaml
│   ├── inventory/           # 재고실사 인스턴스 (매장별 분리)
│   │   ├── wangsimni.yaml
│   │   ├── mapo.yaml
│   │   ├── wolgye.yaml
│   │   └── inbound/         # 입고기록 (매장별 분리)
│   │       ├── wangsimni.yaml
│   │       ├── mapo.yaml
│   │       └── wolgye.yaml
│   ├── production/          # 생산계획 인스턴스 (매장별 분리)
│   │   ├── wangsimni.yaml
│   │   ├── mapo.yaml
│   │   └── wolgye.yaml
│   └── sales/               # 매출기록 인스턴스 (매장별 분리)
│       ├── wangsimni.yaml
│       ├── mapo.yaml
│       └── wolgye.yaml
└── CHANGE_REQUESTS.md   # 변경 요청 기록
```

## 클래스 관계도

```
Store (매장)
  └─ carries ──→ Product (제품)
  │                 └─ forProduct ←── Recipe (레시피)
  │                 │                     └─ uses ──→ Ingredient (재료)
  │                 │                                     └─ forIngredient ←── PurchaseSpec (발주규격)
  │                 │                                                               └─ forPurchaseSpec ←── PriceHistory (가격이력)
  │                 ├─ forProduct ←── ProductionPlan (생산계획)
  │                 └─ forProduct ←── SalesRecord (매출기록)
  ├─ atStore ←── InventorySnapshot (재고실사)
  ├─ atStore ←── ProductionPlan (생산계획)
  └─ atStore ←── SalesRecord (매출기록)
```

**데이터 흐름 요약**
- 매장마다 판매하는 **제품**이 있다
- 제품마다 매장별 **레시피**가 있다 (같은 제품도 매장마다 레시피가 다를 수 있음)
- 레시피는 **재료**를 사용량(amount)과 함께 참조한다
- 재료는 **발주규격**으로 시장에서 주문한다 (발주명·발주단위)
- 발주규격마다 날짜별 **가격이력**이 쌓인다 → 현재 단가 = 해당 pspec + vendor의 가장 최신 레코드
- 매장별 **재고실사**를 주기적으로 기록한다 (재료 단위)
- 매주 매장별 **생산계획**을 입력한다 → 레시피 기반 재료 소요량 및 발주 예상 계산
- 매출은 매장별 **매출기록**에 수기 입력한다

---

## ID 출력 금지 규칙

> **사용자에게 결과를 출력할 때 내부 ID를 절대 그대로 노출하지 말 것.**
> 모든 ID는 반드시 사람이 읽을 수 있는 이름으로 변환해서 출력한다.

| ID 종류 | 변환 방법 | 예시 |
|---------|---------|------|
| `ing_*` | ingredients.yaml의 `name` 필드 | ing_낙지 → 낙지 |
| `pspec_*` | purchase_specs.yaml의 `orderName` 필드 | pspec_058 → 밀키트(탕)용기 32225(중) |
| `ph_*` | 출력 불필요, 단가·날짜·vendor만 표시 | — |
| `prod_*` | products.yaml의 `name` 필드 | prod_mk_013 → 문어전복해물탕 |
| `store_*` | stores.yaml의 `name` 필드 | store_wolgye → 월계점 |

---

## 매장별 납품업체(vendor) 우선순위

> **원가 계산 시 반드시 아래 vendor를 우선 적용할 것.**
> 해당 vendor의 가격이 없을 경우에만 다른 vendor 가격을 사용하고, 출처를 명시한다.

| 매장 | 기본 vendor |
|------|------------|
| 왕십리 (store_wangsimni) | 남선푸드 |
| 마포 (store_mapo) | 남선푸드 |
| 월계 (store_wolgye) | **대영상사** |

### 대영상사 배송비 (원가에 반드시 가산)

> 대영상사 품목은 price_history의 unitPrice에 배송비가 포함되지 않는다.
> 원가 계산 시 아래 배송비를 박스(발주단위)당 추가한다.

| 품목 | 박스당 배송비 |
|------|------------|
| 전복 | 5,000원 |
| 그 외 전체 | 3,000원 |

```
대영상사 재료 실제 원가 = (unitPrice + 배송비) ÷ 발주수량(g)
예) 자숙문어 10kg 1박스 50,000원 → 실제 비용 53,000원 → 원가/g = 53,000 ÷ 10,000 = 5.3원/g
```

---

## 사용 예시

> **⚠️ 단가 vs 판매가격 구분**
> - "단가", "얼마야", "가격" → 직원이 재료에 대해 물어보는 것 = **매입 단가**
>   → ingredients.yaml → purchase_specs.yaml → price_history.yaml 순서로 조회
>   → products.yaml을 절대 보지 말 것
> - "판매가", "소비자가", "팔 때 얼마" → 제품 판매가격
>   → products.yaml의 price 필드 조회
> - 직원이 재료명(문어, 낙지, 새우 등)을 언급하면 무조건 매입 단가 조회로 처리한다

### 예시 1: 특정 재료의 현재 단가 조회

> **주의**: 가격 데이터는 price_history.yaml에 반드시 있다. 아래 순서를 끝까지 실행하기 전에 "데이터 없음"이라고 판단하지 말 것.

```
Step 1. ingredients.yaml → 재료명으로 ID 검색
        - 검색은 부분 일치로 한다 (예: "자숙문어" → ing_자숙문어, ing_자숙문어_절단 모두 검색)
        - ID가 여러 개 나오면 사용자에게 어떤 종류인지 먼저 물어볼 것
        - ID가 하나여도 Step 2에서 pspec이 여러 개일 수 있으므로 반드시 계속 진행

Step 2. purchase_specs.yaml → forIngredient 값이 해당 ID인 항목 전체 조회
        - 반드시 파일 전체를 스캔해서 해당 ID를 참조하는 pspec을 모두 찾을 것
        - pspec이 여러 개면 발주명·발주단위를 함께 나열하고 사용자에게 선택 요청
          예) "자숙문어에 발주규격이 2가지 있습니다:
               1. 국산문어(국산) 8kg
               2. 냉동자숙문어(필리핀) 10kg
               어떤 규격 단가가 필요하신가요?"
        - pspec이 하나뿐이면 바로 Step 3으로

Step 3. price_history.yaml → 해당 pspec ID를 forPurchaseSpec으로 갖는 레코드 전체 조회
        - 반드시 파일 전체를 스캔할 것 (순번 순서대로 나열되어 있지 않을 수 있음)
        - date 기준 가장 최신 레코드의 unitPrice 사용
        - vendor가 여러 개면 vendor별로 최신 단가를 각각 표시

Step 4. 단가 계산 — 레시피 unit에 따라 다름
        [unit = g 인 경우]
          단가/g = unitPrice ÷ (발주kg × 1000)
          재료 원가 = 단가/g × amount(g)

        [unit = 마리·개 인 경우]
          반드시 pspec의 countPerKg 확인
          1마리 무게(g) = 1000 ÷ countPerKg
          단가/g = unitPrice ÷ (발주kg × 1000)
          1마리 원가 = 단가/g × (1000 ÷ countPerKg)
          재료 원가 = 1마리 원가 × amount(마리)
          예) 전복 25미 1kg 18,000원, 레시피 1마리:
              단가/g = 18,000 ÷ 1,000 = 18원/g
              1마리 무게 = 1,000 ÷ 25 = 40g
              1마리 원가 = 18원 × 40g = 720원

        [unit = 팩 인 경우]
          pspec의 orderUnit에서 팩당 용량 확인 후 계산
          예) 해물탕소스 100g×150팩 15kg 103,500원, 레시피 2팩:
              1팩 = 100g
              단가/g = 103,500 ÷ 15,000 = 6.9원/g
              2팩 원가 = 6.9 × 100 × 2 = 1,380원

        결과 출력 시 pspec 발주명·날짜·vendor도 함께 표시
```

### 예시 2: 레시피 원가 계산

```
Step 1. recipes/{매장}.yaml → 해당 레시피 조회, uses·packaging 목록 확인

[재료 원가]
Step 2. 각 재료 ID → ingredients.yaml → thawLossRate, trimLossRate 확인
        - null이면 0%로 처리 (실수율 계산에서 해당 항목을 1.0으로 취급)
        - 예) thawLossRate=15, trimLossRate=null → 실수율 = (1-0.15) × 1.0 = 0.85
Step 3. 재료 ID → purchase_specs.yaml → forIngredient로 pspec 찾기
Step 4. pspec → price_history.yaml → 최신 unitPrice 확인 (vendor 구분)
Step 5. 원가 계산:
          thaw = thawLossRate가 null이면 0, 아니면 해당 값
          trim = trimLossRate가 null이면 0, 아니면 해당 값
          실수율 = (1 - thaw/100) × (1 - trim/100)
          원가/g = unitPrice ÷ (발주kg × 1000) ÷ 실수율
          재료 원가 = 원가/g × amount(g)
        - 손실률이 하나라도 입력된 경우: 결과에 실수율(%)을 표시
        - 둘 다 null인 경우: "(손실률 미입력)" 표시
Step 6. 전체 재료 합산 = 재료비 합계

[포장재 원가]
Step 7. packaging 목록 → 각 pspec → price_history.yaml → 최신 unitPrice 확인
Step 8. 포장재 1개 단가 = unitPrice ÷ 발주수량
        포장재 원가 = 1개 단가 × quantity
Step 9. 전체 포장재 합산 = 포장재비 합계

[최종]
Step 10. 레시피 1팩 원가 = 재료비 합계 + 포장재비 합계
```

### 예시 3: 레시피 설계 / 변경 가이드

> **트리거**: "레시피 새로 짜고 싶어", "레시피 바꾸고 싶어", "원가 줄이고 싶어" 등

```
─── STEP 1. 신규 vs 변경 분기 ────────────────────────────

  [기존 레시피 변경]
    - 상품명·매장 확인 → products.yaml·recipes에서 자동 조회
    - 소비자가 자동 참조
    → STEP 2로

  [신규 레시피]
    아래 순서로 확인:
    1) 상품명
    2) 카테고리 (밀키트 / 단품 / 게장류)
    3) 소비자가 (사용자가 결정)
    4) 유사한 기존 상품이 있으면 참고용으로 보여줄지 물어볼 것
    ※ 매장은 레시피 확정 후 STEP 4에서 선택
    → STEP 2로

─── STEP 2. 원가 한도 제시 ───────────────────────────────
  총 원가 한도 = 소비자가 × 0.3705

  [밀키트인 경우] 고정비 차감:
    - 밀키트 용기: pspec → price_history로 1개 단가 계산
    - 콩나물팩: 1,200원
    - 소스: pspec → price_history로 1팩 단가 계산
    수산물 재료 예산 = 총 원가 한도 - 고정비 합계

  [단품인 경우] 용기비만 차감 (소스·콩나물팩 해당 없으면 생략)

  출력 예시:
  ┌────────────────────────────────────┐
  │ 소비자가     19,800원              │
  │ 총 원가 한도  7,335원 (×0.3705)   │
  │ 고정비 차감                        │
  │   용기        xxx원                │
  │   콩나물팩  1,200원                │
  │   소스        xxx원                │
  │ ─────────────────────────         │
  │ 재료 예산    x,xxx원 ← 이 안에서  │
  └────────────────────────────────────┘

─── STEP 3. 재료 구성 협의 ───────────────────────────────
  [기존 레시피 변경]
    현재 레시피 원가를 예시 2 방식으로 먼저 계산해서 보여준다
    현재 원가 vs 한도 → 초과/여유 금액 표시 후 협의 시작

  [신규]
    "주재료가 뭔가요?"부터 시작
    재료 하나씩 추가할 때마다 누적 원가 업데이트

  재료 추가 시마다 아래 표 갱신:
  ┌──────────────────────────────────────────┐
  │ 재료          양   단가/g  원가   누적   │
  │ 낙지         230g  x.xx원  xxx원  xxx원  │
  │ 솔방울오징어 150g  x.xx원  xxx원  xxx원  │
  │ ...                                      │
  │ ──────────────────────────────────────  │
  │ 재료비  x,xxx원  /  예산  x,xxx원       │
  │ 여유   +xxx원  ← 추가 재료 가능         │
  │ (초과 시 "xxx원 초과 — 양 조절 필요")   │
  └──────────────────────────────────────────┘

─── STEP 4. 확정 및 저장 ─────────────────────────────────
  최종 레시피 요약 출력 후 사용자 확인 받기

  [기존 변경] → recipes/{매장}.yaml 해당 레코드 수정
  [신규]
    1) 적용할 매장 선택 (복수 가능)
    2) products.yaml에 매장별 신규 상품 추가 (id 자동 채번)
    3) recipes/{매장}.yaml에 신규 레시피 추가
    두 파일 모두 저장 후 안내
    ※ 여러 매장에 동일 레시피 적용 시 매장마다 별도 레코드 생성
```

### 예시 4: 매장별 제품 목록 조회

```
products.yaml → soldAt 배열에 해당 store_* id 포함된 항목 필터
belongsTo로 카테고리 구분 (cat_mealkit / cat_single / cat_ganjang)
```

### 예시 5: 개수 기준 재료(전복 등) 원가

```
purchase_specs.yaml → countPerKg 확인 (예: 25미 → 1개 평균 40g)
price_history.yaml → 최신 unitPrice
1개 원가 = unitPrice (전복은 orderUnit이 1개 기준)
```

### 예시 6: 생산계획 등록 (일별, 주 단위)

```
Step 1. 대상 상품·매장·주 시작일(월요일) 확인
Step 2. 요일별 계획 수량 확인 (0이면 0으로 입력)
Step 3. production/{매장}.yaml에 새 레코드 추가
        id: plan_{매장약어}_{weekStart(YYYYMMDD)}_{prod_id약어}
        dailyPlan: {mon: n, tue: n, wed: n, thu: n, fri: n, sat: n, sun: n}
        status: planned
Step 4. 총 계획량 = dailyPlan 합산값 안내

조정 시:
  - dailyPlan은 수정하지 말 것
  - dailyAdjusted에 변경된 요일만 추가 (예: {sat: 25})
  - status: in_progress로 변경

실제 생산 완료 후:
  - dailyActual 입력
  - 모든 요일 완료 시 status: completed
```

### 예시 7: 입고 기록

```
Step 1. 발주규격(pspec) 확인 — 재료명 또는 발주명으로 검색
Step 2. 입고일, 수량, 단위 확인
Step 3. inventory/inbound/{매장}.yaml에 새 레코드 추가
        id: inbound_{매장약어}_YYYYMMDD_{순번}
        date: YYYY-MM-DD
        quantity: 입고 수량 (발주단위 기준)
        unit: 발주단위와 동일
Step 4. 입고 완료 안내
```

### 예시 8: 발주 필요량 계산

```
Step 1. 대상 매장·주 생산계획 확인 (production/{매장}.yaml)
        유효 일별 수량 = dailyAdjusted 있으면 해당 요일 override, 없으면 dailyPlan 사용
        주간 총 생산량 = 유효 일별 수량 합산

Step 2. 레시피별 재료 소요량 계산
        각 재료:
          실수율 = (1 - thawLossRate/100) × (1 - trimLossRate/100)  ← null이면 0으로
          순소요량(g) = 레시피 amount × 총생산량
          발주소요량(g) = 순소요량 ÷ 실수율
        동일 재료가 여러 레시피에 쓰이면 합산

Step 3. 현재 이론 재고 계산 (재료별)
        기준재고 = 해당 매장 최근 InventorySnapshot 수량 (단위 통일)
        실사 이후 입고 = InboundRecord 중 실사일 이후 입고분 합산 (발주단위 → g 변환)
        실사 이후 소모 = 실사일 이후 완료(completed) 생산분 × 레시피 재료량 ÷ 실수율
        이론재고 = 기준재고 + 입고 - 소모

Step 4. 발주 필요량 = 발주소요량 - 이론재고
        음수(재고 충분)면 "재고 충분" 표시
        양수면 발주 필요량 안내 (pspec 발주단위로 올림 계산)

Step 5. 결과 출력 예시:
        재료명 | 소요량 | 현재재고 | 발주필요 | 발주단위
        낙지   | 3,450g | 2,000g  | 1,450g  | 최소 1박스(5kg) 권장
```

---

## 레시피 설계 원가 기준

> **모든 매장 공통** 수수료 기준으로 레시피를 설계할 때 사용한다.

```
[수수료]
  이마트 수수료: 22% (전 매장 공통)
  납품업체 수수료: 5% (전 매장 공통)

[총 원가 한도 계산]
  총 원가 한도 = 소비자가 ÷ 2 × (1 - 0.22) × (1 - 0.05)
              = 소비자가 × 0.3705

  예) 소비자가 19,800원
      → 19,800 ÷ 2 = 9,900원  (50% 할인 기준 최악 시나리오)
      → 9,900 × 0.78 = 7,722원  (이마트 수수료 차감)
      → 7,722 × 0.95 = 7,335원  (납품업체 수수료 차감)
      → 총 원가 한도 = 7,335원

[재료 예산 계산 — 밀키트 기준]
  재료 예산 = 총 원가 한도
            - 밀키트 용기값
            - 양배추콩나물세트: 1,500원 (pspec_086, 다삼인삼)
            - 소스값
            (= 수산물·육류 재료에 쓸 수 있는 예산)
```

> **봇 활용**: 레시피 원가 계산(예시2) 결과와 이 한도를 비교하면
> 현재 레시피가 수익 구조 내에 있는지 즉시 확인 가능.

---

## 원가 계산 공식

```
thaw = thawLossRate (null이면 0)
trim = trimLossRate (null이면 0)
실수율 = (1 - thaw/100) × (1 - trim/100)   ← 1.0이면 손실 없음

원가/g = unitPrice ÷ (발주kg × 1000) ÷ 실수율

개수 기준 재료:
  1개 평균 무게(g) = 1000 ÷ countPerKg
  1개 원가          = 원가/g × 1개 평균 무게

레시피 1팩 원가 = Σ (재료별 원가) + 포장재비 합계

※ 손실률이 입력된 재료는 원가 옆에 "실수율 XX%" 표시
※ 손실률 미입력 재료는 "(손실률 미입력)" 표시
```

---

## 인스턴스 CRUD 규칙

> **⚠️ 데이터 임의 입력 금지**
> `waterbe/instances/` 하위 모든 파일에 데이터를 추가하거나 수정할 때는 **반드시 사용자에게 먼저 확인**을 받아야 한다.
> 재료 구성이 불명확하면 추측으로 채우지 말고 사용자에게 물어볼 것.

> **⚠️ PriceHistory 수정 금지**
> 가격이 변경되면 기존 레코드를 수정하지 말고 **반드시 새 레코드를 추가**할 것.

### ID 명명 규칙
| 클래스 | 접두사 | 예시 |
|--------|--------|------|
| Store | `store_` | `store_wangsimni` |
| Category | `cat_` | `cat_mealkit` |
| Product (밀키트) | `prod_mk_` | `prod_mk_001` |
| Product (단품) | `prod_sp_` | `prod_sp_001` |
| Product (게장류) | `prod_gj_` | `prod_gj_001` |
| Ingredient | `ing_` | `ing_낙지`, `ing_흰다리새우살_L_페루` |
| Recipe | `recipe_{매장}_{product_id}` | `recipe_wangsimni_mk001` |
| PurchaseSpec | `pspec_` + 순번 | `pspec_001` |
| PriceHistory | `ph_` + 순번 | `ph_001` |
| InventorySnapshot | `snap_{매장약어}_YYYYMMDD_{재료약어}` | `snap_ws_20260315_낙지` |
| ProductionPlan | `plan_{매장약어}_YYYYMMDD_{prod_id약어}` | `plan_ws_20260317_mk001` |
| SalesRecord | `sale_{매장약어}_YYYYMMDD_{prod_id약어}` | `sale_ws_20260315_mk001` |

### Ingredient ID 분리 기준

- **기본형**: `ing_{재료명}` — 원산지·성분 구분 불필요 (예: `ing_낙지`, `ing_콩나물`)
- **크기·등급**: `ing_{재료명}_{L|S}_{원산지}` (예: `ing_흰다리새우살_L_페루`)
- **산지만 다른 경우**: 산지명 suffix (예: `ing_게_이탈리아`, `ing_게_바레인`)
- **성분·알레르기가 다르면** → ID 분리 / **업체만 다르면** → 같은 ID

### 추가 (Create)
- 새 인스턴스는 파일 맨 끝에 추가
- `id`는 해당 접두사의 마지막 번호 + 1
- `class` 필드는 `schema.yaml`의 클래스명과 정확히 일치해야 함
- `relations`의 참조 id가 실제로 존재하는지 확인

### 조회 (Read)
- 매장별 제품: `products.yaml`에서 `soldAt`에 해당 store id 포함 항목 필터
- 카테고리별 제품: `products.yaml`에서 `belongsTo`가 해당 cat id인 항목 필터

### 수정 (Update)
- 가격·단위 변경: 해당 인스턴스의 `data` 블록만 수정
- 매장 이전/추가: `soldAt` 배열에 store id 추가 또는 제거

### 삭제 (Delete)
- 삭제 전 다른 인스턴스의 `relations`에서 해당 id 참조 여부 확인
- Store 삭제 시: `products.yaml`의 `soldAt` 및 `recipes/{store}.yaml`의 `atStore` 참조 제거
- Ingredient 삭제 시: `recipes/` 하위 모든 파일의 `uses`에서 해당 id 참조 제거

---

## 스키마 수정 규칙

1. **하위 호환성 유지**: 기존 속성 삭제·타입 변경 시 인스턴스 파일 전체 먼저 점검
2. **버전 관리**: 수정 시마다 `schema.yaml`의 `version` 필드를 올린다
3. **새 클래스·속성 추가**: 기존 인스턴스에 영향 없으면 자유롭게 추가 가능
4. **관계 변경**: `cardinality` 변경 시 인스턴스 값이 배열인지 단일값인지 확인 후 일괄 수정

---

## 현재 미완료 데이터

### 가격 미확인
- `prod_sp_007` (국산흑골뱅이, 왕십리): `price: null`
- pspec 가격 미입력 (남선푸드): pspec_004, pspec_048, pspec_051, pspec_057, pspec_064
- ※ pspec_015, pspec_042 → 대영상사 단가 입력 완료
- 대영상사 단가: 2026-03-16 기준 입력 완료 (ph_079~098) / 최신 pspec: pspec_085

### pspec 없는 재료 (원가 계산 불가)
- ing_골뱅이, ing_게_이탈리아, ing_볼락, ing_염지소대창
- ※ ing_찜소스 → 레시피에서 ing_만능찜소스(pspec_074)로 교체 완료
- ※ ing_명태곤이 → pspec_082(대영상사) 추가 완료

### 레시피 재료 미입력
- 왕십리 mk_005 시원한 새우탕: 보류
- 왕십리 mk_006 골뱅이탕: 보류
- 왕십리 gj001 국산 알베기 간장게장: `uses: []`
- 왕십리 gj002 간장게장: `uses: []`
- 월계 sp_015 가리비관자: `uses: []`

### 재료 데이터 미입력
- composition/allergen 미입력: ing_비자숙문어, ing_자숙문어_절단, ing_냉동홍가리비, ing_반각가리비, ing_새우_사우디, ing_양념게장소스, ing_우삼겹
- ingredientType: 전 재료 미입력 (나중에 일괄 입력 예정)

### 운영 데이터 미입력
- 재고실사: inventory/ 전체 비어있음 (첫 실사 입력 대기)
- 생산계획: production/ 전체 비어있음
- 매출기록: sales/ 전체 비어있음

### 미구현 기능
- Ingredient.vendor 필드: 납품업체별 재료 관리 (PriceHistory.vendor는 구현 완료)
- Store.defaultVendor: 매장별 기본 거래처 (왕십리·마포 = 남선푸드, 월계 = 대영상사)
