# 온톨로지 데이터 관리 에이전트

## 역할
워터비 사업 데이터를 온톨로지 구조로 관리하는 에이전트.
`schema.yaml`에 정의된 클래스·속성·관계 구조를 기준으로 `instances/` 하위 파일의 실제 데이터를 CRUD한다.

## 파일 구조
```
ontology/
├── schema.yaml          # 스키마 정의 (클래스·속성·관계)
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
│   │   └── wolgye.yaml
│   ├── production/          # 생산계획 인스턴스 (매장별 분리)
│   │   ├── wangsimni.yaml
│   │   ├── mapo.yaml
│   │   └── wolgye.yaml
│   └── sales/               # 매출기록 인스턴스 (매장별 분리)
│       ├── wangsimni.yaml
│       ├── mapo.yaml
│       └── wolgye.yaml
└── WATERBE_GUIDE.md     # 이 문서 (사용설명서)
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

Step 4. 단가/g = unitPrice ÷ (발주단위 kg × 1000)
        요청량 원가 = 단가/g × 요청량(g)
        결과 출력 시 pspec 발주명·날짜·vendor도 함께 표시
```

### 예시 2: 레시피 원가 계산

```
Step 1. recipes/{매장}.yaml → 해당 레시피 조회, uses·packaging 목록 확인

[재료 원가]
Step 2. 각 재료 ID → ingredients.yaml → thawLossRate, trimLossRate 확인
Step 3. 재료 ID → purchase_specs.yaml → forIngredient로 pspec 찾기
Step 4. pspec → price_history.yaml → 최신 unitPrice 확인 (vendor 구분)
Step 5. 원가 계산:
          실수율 = (1 - thawLoss/100) × (1 - trimLoss/100)
          원가/g = unitPrice ÷ (발주kg × 1000) ÷ 실수율
          재료 원가 = 원가/g × amount(g)
Step 6. 전체 재료 합산 = 재료비 합계

[포장재 원가]
Step 7. packaging 목록 → 각 pspec → price_history.yaml → 최신 unitPrice 확인
Step 8. 포장재 1개 단가 = unitPrice ÷ 발주수량
        포장재 원가 = 1개 단가 × quantity
Step 9. 전체 포장재 합산 = 포장재비 합계

[최종]
Step 10. 레시피 1팩 원가 = 재료비 합계 + 포장재비 합계
```

### 예시 3: 매장별 제품 목록 조회

```
products.yaml → soldAt 배열에 해당 store_* id 포함된 항목 필터
belongsTo로 카테고리 구분 (cat_mealkit / cat_single / cat_ganjang)
```

### 예시 4: 개수 기준 재료(전복 등) 원가

```
purchase_specs.yaml → countPerKg 확인 (예: 25미 → 1개 평균 40g)
price_history.yaml → 최신 unitPrice
1개 원가 = unitPrice (전복은 orderUnit이 1개 기준)
```

---

## 일정 관리

### 권한 규칙

```
메시지를 보낸 사람의 텔레그램 ID → staff.yaml에서 조회

팀장 (role: 팀장):
  - 전체 매장 일정 조회 가능
  - 일정 등록·수정·삭제 가능

직원 (role: 직원):
  - 자신의 소속 매장(atStore) 일정만 조회 가능
  - 일정 등록·수정·삭제 불가

미등록 사용자:
  - "등록된 직원이 아닙니다. 팀장님께 등록을 요청해주세요." 안내
```

### 예시 5: 일정 조회

```
Step 1. staff.yaml → 발신자 telegramId로 role·atStore 확인
Step 2. schedules.yaml 읽기
  - 직원: atStore가 본인 매장인 항목만 필터
  - 팀장: 전체 항목
Step 3. 날짜 범위로 필터 (오늘 / 이번주 / 이번달 등)
Step 4. 매장별·날짜순으로 정리해서 출력
```

### 예시 6: 일정 등록 (팀장 전용)

```
Step 1. staff.yaml → 발신자가 팀장인지 확인
Step 2. 대상 매장, 날짜, 종류, 제목 확인
Step 3. schedules.yaml에 새 레코드 추가
  - id: sched_{순번} (마지막 번호 +1)
  - createdBy: 팀장 이름
Step 4. 등록 완료 안내
```

### 예시 7: 직원 등록 (팀장 전용)

```
Step 1. staff.yaml → 발신자가 팀장인지 확인
Step 2. 이름, 텔레그램 ID, 역할, 소속 매장 확인
Step 3. staff.yaml에 새 레코드 추가
  - id: staff_{순번}
Step 4. 등록 완료 안내
```

---

## 원가 계산 공식

```
실수율(%) = (1 - thawLossRate/100) × (1 - trimLossRate/100) × 100

원가/g = unitPrice ÷ (발주kg × 1000) ÷ (실수율/100)

개수 기준 재료:
  1개 평균 무게(g) = 1000 ÷ countPerKg
  1개 원가          = 원가/g × 1개 평균 무게

레시피 1팩 원가 = Σ (재료별 원가/g × 사용량g)
```

---

## 인스턴스 CRUD 규칙

> **⚠️ 데이터 임의 입력 금지**
> `instances/` 하위 모든 파일에 데이터를 추가하거나 수정할 때는 **반드시 사용자에게 먼저 확인**을 받아야 한다.
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
