# 온톨로지 데이터 관리 에이전트

## 역할
워터비 사업 데이터를 온톨로지 구조로 관리하는 에이전트.
`schema.yaml`에 정의된 클래스·속성·관계 구조를 기준으로 `instances/` 하위 파일의 실제 데이터를 CRUD한다.

## 파일 구조
```
ontology/
├── schema.yaml          # 스키마 정의 (클래스·속성·관계)
├── instances/
│   ├── stores.yaml      # 매장 인스턴스
│   ├── products.yaml    # 제품 인스턴스
│   ├── categories.yaml  # 카테고리 인스턴스
│   ├── ingredients.yaml # 재료 인스턴스
│   └── recipes.yaml     # 레시피 인스턴스
└── AGENT.md             # 이 문서
```

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
| Ingredient | `ing_` | `ing_낙지`, `ing_흰다리새우살_L`, `ing_흰다리새우살_S` |
| Recipe | `recipe_{매장}_{product_id}` | `recipe_wangsimni_mk001` |

### 크기·등급 구분 표기
- 같은 재료라도 크기·등급이 달라 성분이나 원산지가 다를 경우 suffix로 구분
  - `_L`: 대형 / 꼬리 있음 등 (예: `ing_흰다리새우살_L`)
  - `_S`: 소형 / 일반 등 (예: `ing_흰다리새우살_S`)
- 산지가 달라 별도 구분이 필요한 경우: 산지명 suffix (예: `ing_게_이탈리아`, `ing_게_바레인`)
- 구분 불필요한 재료는 suffix 생략 (예: `ing_콩나물`, `ing_낙지`)

### 추가 (Create)
- 새 인스턴스는 파일 맨 끝에 추가.
- `id`는 해당 접두사의 마지막 번호 + 1.
- `class` 필드는 `schema.yaml`에 정의된 클래스명과 정확히 일치해야 한다.
- `relations`의 참조 id가 해당 인스턴스 파일에 실제로 존재하는지 확인.

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
- Store 삭제 시: `products.yaml`의 `soldAt`에서 해당 id 제거, `recipes.yaml`의 `atStore` 참조도 제거.
- Category 삭제 시: `products.yaml`의 `belongsTo` 참조 제품 처리 후 삭제.
- Ingredient 삭제 시: `recipes.yaml`의 `uses`에서 해당 id 참조 제거.
- Recipe 삭제 시: 다른 인스턴스에서 참조하지 않으므로 단독 삭제 가능.

## 검증 체크리스트

작업 완료 후 아래 항목을 확인한다:

- [ ] `schema.yaml`의 클래스명과 인스턴스의 `class` 필드가 일치하는가?
- [ ] 모든 `relations` 참조 id가 해당 파일에 실제로 존재하는가?
- [ ] 새 Product의 `soldAt`에 최소 하나의 Store id가 있는가?
- [ ] `price: null`인 항목은 의도된 미기입인가 (임시)? 향후 확정 후 업데이트 필요.
- [ ] `Category.subClassOf`에 순환 참조가 없는가?
- [ ] Recipe의 `(forProduct, atStore)` 조합이 `recipes.yaml` 내에서 중복되지 않는가?
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

### vendor (납품업체) 관리 — 미구현
- 설계 확정: 방법 C 채택
  - 업체만 다르고 성분·알레르기 동일 → 같은 ID, `vendor` 배열 필드로 관리
  - 성분·알레르기가 다르면 → ID 분리 (`_2`, `_3` suffix)
  - 레시피는 성분 기준 ID 참조 → 업체 교체 시 레시피 변동 없음
- 구현 시 필요한 작업:
  - schema.yaml에 `vendor: list<string>` 필드 추가 (nullable)
  - 각 재료에 vendor 입력
  - AGENT.md 분리 기준 명문화
