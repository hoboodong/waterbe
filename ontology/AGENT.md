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
| Ingredient | `ing_` | `ing_문어` |
| Recipe | `recipe_{매장}_{product_id}` | `recipe_wangsimni_mk001` |

### 추가 (Create)
- 새 인스턴스는 파일 맨 끝에 추가.
- `id`는 해당 접두사의 마지막 번호 + 1.
- `class` 필드는 `schema.yaml`에 정의된 클래스명과 정확히 일치해야 한다.
- `relations`의 참조 id가 해당 인스턴스 파일에 실제로 존재하는지 확인.

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
- `price: null` — `prod_sp_007` (국산흑골뱅이): 가격 확인 후 업데이트 필요
- 마포점·월계점 제품 라인업: 아직 미입력 (데이터 확보 후 products.yaml에 추가)
- 레시피: 왕십리점 `prod_mk_001` 1개만 입력됨 — 나머지 상품 레시피 추가 필요
