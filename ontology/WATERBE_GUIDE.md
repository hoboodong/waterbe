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
│   ├── products.yaml        # 제품 인스턴스
│   ├── categories.yaml      # 카테고리 인스턴스
│   ├── ingredients.yaml     # 재료 인스턴스
│   ├── purchase_specs.yaml  # 발주규격 인스턴스
│   ├── price_history.yaml   # 가격이력 인스턴스
│   └── recipes/             # 레시피 인스턴스 (매장별 분리)
│       ├── wangsimni.yaml
│       ├── mapo.yaml
│       └── wolgye.yaml
└── WATERBE_GUIDE.md     # 이 문서 (사용설명서)
```

## 클래스 관계도

```
Store (매장)
  └─ carries ──→ Product (제품)
                    └─ forProduct ←── Recipe (레시피)
                                          └─ uses ──→ Ingredient (재료)
                                                          └─ forIngredient ←── PurchaseSpec (발주규격)
                                                                                    └─ forPurchaseSpec ←── PriceHistory (가격이력)
```

**데이터 흐름 요약**
- 매장마다 판매하는 **제품**이 있다
- 제품마다 매장별 **레시피**가 있다 (같은 제품도 매장마다 레시피가 다를 수 있음)
- 레시피는 **재료**를 사용량(amount)과 함께 참조한다
- 재료는 **발주규격**으로 시장에서 주문한다 (발주명·발주단위)
- 발주규격마다 날짜별 **가격이력**이 쌓인다 → 현재 단가 = 해당 pspec + vendor의 가장 최신 레코드

---

## 사용 예시

### 예시 1: 왕십리점 낙곱새 레시피 원가 계산
```
1. recipes/wangsimni.yaml → recipe_wangsimni_mk010 조회
2. uses 목록에서 재료별 (ingredient, amount, unit) 확인
3. 각 재료 ID → ingredients.yaml → thawLossRate, trimLossRate 확인
4. 재료 ID → purchase_specs.yaml → forIngredient 역참조로 pspec 찾기
5. pspec ID → price_history.yaml → 가장 최신 date의 unitPrice 확인
6. 원가 계산:
   실수율 = (1 - thawLoss/100) × (1 - trimLoss/100)
   원가/g = unitPrice ÷ (발주kg × 1000) ÷ 실수율
   재료 원가 = 원가/g × amount(g)
7. 전체 재료 합산 = 레시피 1팩 원가
```

### 예시 2: 특정 재료의 현재 단가 조회 (필수 패턴 — 반드시 이 순서로)

> **주의**: 가격 데이터는 price_history.yaml에 있다. "데이터 없음"이라고 판단하기 전에 반드시 아래 4단계를 모두 실행할 것.

```
[질문 예시] "자숙문어 200g 얼마야?"

Step 1. 재료 ID 확인
  → ingredients.yaml 에서 재료명 검색
  → 예: 자숙문어 관련 ID = ing_자숙문어 (필리핀), ing_비자숙문어 (국산) 등
  → ID가 여러 개면 사용자에게 어떤 종류인지 먼저 물어볼 것

Step 2. pspec 찾기
  → purchase_specs.yaml 에서 forIngredient 값이 해당 ID인 항목 전체 조회
  → 예: ing_자숙문어 → pspec_024 (국산문어 8kg), pspec_026 (냉동자숙문어 필리핀 10kg)
  → pspec가 여러 개면 전부 나열하고 사용자에게 선택 요청

Step 3. 가격 조회
  → price_history.yaml 에서 해당 pspec ID를 forPurchaseSpec으로 갖는 레코드 조회
  → date 기준 최신 레코드의 unitPrice 사용
  → vendor 필드도 함께 확인 (남선푸드 / 대영상사 등)

Step 4. 단가 계산
  → 단가/g = unitPrice ÷ (발주kg × 1000)
  → 요청량 원가 = 단가/g × 요청량(g)

[실제 계산 예시]
  냉동자숙문어(필리핀) 200g:
    ph_021 → unitPrice: 153,000원 / 10kg
    단가/g = 153,000 ÷ 10,000 = 15.3원/g
    200g 원가 = 15.3 × 200 = 3,060원

  국산문어 200g:
    ph_019 → unitPrice: 245,000원 / 8kg
    단가/g = 245,000 ÷ 8,000 = 30.625원/g
    200g 원가 = 30.625 × 200 = 6,125원
```

### 예시 3: 매장별 제품 목록 조회
```
1. products.yaml → soldAt 배열에 store_wangsimni 포함된 항목 필터
2. belongsTo로 카테고리 구분 (cat_mealkit / cat_single / cat_ganjang)
```

### 예시 4: 개수 기준 재료(전복 등) 원가
```
1. purchase_specs.yaml → pspec_022 (전복 소) → countPerKg: 25
2. 1개 평균 무게 = 1000 ÷ 25 = 40g
3. price_history.yaml → 최신 unitPrice (예: 18,000원/개)
4. 레시피에 전복 1개 → 원가 18,000원
```

---

## 스키마 수정 규칙

1. **하위 호환성 유지**: 기존 속성을 삭제하거나 타입을 변경할 때는 인스턴스 파일 전체를 먼저 점검한다.
2. **버전 관리**: `schema.yaml`의 `version` 필드를 수정 시마다 올린다 (SemVer 마이너 또는 패치).
3. **새 클래스·속성 추가**: 기존 인스턴스에 영향 없으면 자유롭게 추가 가능.
4. **관계 변경**: `cardinality` 변경 시 인스턴스의 관계 값이 배열인지 단일 값인지 확인 후 일괄 수정.

## 인스턴스 CRUD 규칙

### ID 명명 규칙
| 클래스 | 접두사 | 예시 |
|--------|--------|------|
| Store | `store_` | `store_wangsimni` |
| Category | `cat_` | `cat_mealkit` |
| Product (밀키트) | `prod_mk_` | `prod_mk_001` |
| Product (단품) | `prod_sp_` | `prod_sp_001` |
| Product (게장류) | `prod_gj_` | `prod_gj_001` |
| Ingredient | `ing_` | `ing_낙지`, `ing_흰다리새우살_L_페루`, `ing_흰다리새우살_S_베트남` |
| Recipe | `recipe_{매장}_{product_id}` | `recipe_wangsimni_mk001` |
| PurchaseSpec | `pspec_` + 순번 | `pspec_001`, `pspec_002` |
| PriceHistory | `ph_` + 순번 | `ph_001`, `ph_002` |

### Ingredient ID 분리 기준

**기본형**: `ing_{재료명}` — 원산지·성분 구분 불필요한 재료 (예: `ing_콩나물`, `ing_낙지`)

**크기·등급 있는 경우**: `ing_{재료명}_{L|S}_{원산지}`
- `_L`: 대형 / 꼬리 있음 등
- `_S`: 소형 / 일반 등
- 예: `ing_흰다리새우살_L_페루`, `ing_흰다리새우살_S_베트남`

**같은 원산지인데 성분이 다른 경우**: 숫자 suffix 추가
- 예: `ing_흰다리새우살_L_페루_2`

**산지만 다른 경우**: 산지명 suffix
- 예: `ing_게_이탈리아`, `ing_게_바레인`

**ID 분리 원칙**:
- 성분(composition) 또는 알레르기(allergen)가 다르면 → ID 분리
- 업체(vendor)만 다르고 성분·알레르기 동일 → 같은 ID (vendor 필드로 관리, 추후 구현)
- 레시피는 성분 기준 ID 참조 → 업체 교체 시 레시피 변동 없음

### 추가 (Create)
- 새 인스턴스는 파일 맨 끝에 추가.
- `id`는 해당 접두사의 마지막 번호 + 1.
- `class` 필드는 `schema.yaml`에 정의된 클래스명과 정확히 일치해야 한다.
- `relations`의 참조 id가 해당 인스턴스 파일에 실제로 존재하는지 확인.

## 원가 계산 공식

```
실수율(%) = (1 - thawLossRate/100) × (1 - trimLossRate/100) × 100

실제 원가/g  = unitPrice ÷ (발주kg × 1000) ÷ (실수율/100)

개수 기준 재료:
  1개 평균 무게(g) = 1000 ÷ countPerKg
  1개 원가          = 실제 원가/g × 1개 평균 무게

레시피 1팩 원가 = Σ (재료별 실제 원가/g × 사용량g)
```

> **⚠️ PriceHistory 수정 금지**
> 가격이 변경되면 기존 레코드를 수정하지 말고 **반드시 새 레코드를 추가**할 것.
> 현재 단가 = 해당 pspec + vendor의 가장 최신 date 레코드.

> **⚠️ 온톨로지 데이터 임의 입력 절대 금지**
> 모든 인스턴스 데이터(`ingredients.yaml`, `products.yaml`, `recipes.yaml`, `stores.yaml`, `categories.yaml`)에 새 데이터를 추가하거나 기존 데이터를 수정할 때는 **반드시 사용자에게 먼저 확인**을 받아야 한다.
> - 레시피 재료가 없을 경우: 어떤 재료가 필요한지 보고하고 허가를 받은 뒤 추가
> - 재료 구성이 불명확할 경우: 추측으로 채우지 말고 사용자에게 물어볼 것
> - 사용자가 명시적으로 지시한 내용만 입력할 것. 합리적으로 보여도 임의 판단으로 넣지 말 것

### 조회 (Read)
- 매장별 제품 목록: `products.yaml`에서 `soldAt`에 해당 `store_*` id가 포함된 항목 필터.
- 카테고리별 제품 목록: `products.yaml`에서 `belongsTo`가 해당 `cat_*` id인 항목 필터.

### 수정 (Update)
- 가격·단위 변경: 해당 인스턴스의 `data` 블록만 수정.
- 매장 이전/추가: `soldAt` 배열에 store id 추가 또는 제거.

### 삭제 (Delete)
- 인스턴스를 파일에서 제거하기 전에 다른 인스턴스의 `relations`에서 해당 id 참조가 없는지 확인.
- Store 삭제 시: `products.yaml`의 `soldAt`에서 해당 id 제거, `recipes/{store}.yaml`의 `atStore` 참조도 제거.
- Category 삭제 시: `products.yaml`의 `belongsTo` 참조 제품 처리 후 삭제.
- Ingredient 삭제 시: `recipes/` 하위 모든 파일의 `uses`에서 해당 id 참조 제거.
- Recipe 삭제 시: 다른 인스턴스에서 참조하지 않으므로 단독 삭제 가능.

## 검증 체크리스트

작업 완료 후 아래 항목을 확인한다:

- [ ] `schema.yaml`의 클래스명과 인스턴스의 `class` 필드가 일치하는가?
- [ ] 모든 `relations` 참조 id가 해당 파일에 실제로 존재하는가?
- [ ] 새 Product의 `soldAt`에 최소 하나의 Store id가 있는가?
- [ ] `price: null`인 항목은 의도된 미기입인가 (임시)? 향후 확정 후 업데이트 필요.
- [ ] `Category.subClassOf`에 순환 참조가 없는가?
- [ ] Recipe의 `(forProduct, atStore)` 조합이 `recipes/` 전체 파일에서 중복되지 않는가?
- [ ] Recipe의 `uses`에서 참조하는 모든 ingredient id가 `ingredients.yaml`에 존재하는가?

## 현재 미완료 데이터

### 가격 미확인
- `prod_sp_007` (국산흑골뱅이, 왕십리): `price: null` — 확인 후 업데이트 필요

### 레시피 재료 미입력
- 왕십리 `mk_005` 시원한 새우탕: 보류
- 왕십리 `mk_006` 골뱅이탕: 보류
- 왕십리 `gj001` 국산 알베기 간장게장: `uses: []`
- 왕십리 `gj002` 간장게장: `uses: []`
- 월계 `sp_015` 가리비관자: `uses: []`

### 재료 성분(composition) 미입력
- 소스류: ing_해물탕소스, ing_찜소스, ing_낙곱새소스, ing_볶음소스, ing_간장소스
- 기타: ing_오만둥이, ing_순살아귀, ing_주꾸미, ing_홍합, ing_라면, ing_동태 등 일부

### ingredientType 미입력
- 모든 재료에 `ingredientType` 필드 미입력 (나중에 일괄 입력 예정)
- 분류 예시: 1차수산물, 채소, 소스, 양념 등

### 신규 재료 — 데이터 미입력
- ing_비자숙문어: composition, allergen 미입력
- ing_자숙문어_절단: composition, allergen, origin 미입력
- ing_냉동홍가리비: composition, allergen, origin 미입력
- ing_반각가리비: composition, allergen, origin 미입력
- ing_새우_사우디: composition, allergen 미입력
- ing_양념게장소스: composition, allergen, origin 미입력
- ing_우삼겹: composition, allergen 미입력

### vendor (납품업체) 관리 — 미구현
- 설계 확정: 방법 C 채택
  - 업체만 다르고 성분·알레르기 동일 → 같은 ID, `vendor` 배열 필드로 관리
  - 성분·알레르기가 다르면 → ID 분리 (`_2`, `_3` suffix)
  - 레시피는 성분 기준 ID 참조 → 업체 교체 시 레시피 변동 없음
- 구현 시 필요한 작업:
  - schema.yaml에 `vendor: list<string>` 필드 추가 (nullable)
  - 각 재료에 vendor 입력
  - WATERBE_GUIDE.md 분리 기준 명문화
