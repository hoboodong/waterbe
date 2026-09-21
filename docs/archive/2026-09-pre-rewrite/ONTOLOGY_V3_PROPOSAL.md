# Waterbe Ontology v3 Proposal

## 목표

v3는 워터비 데이터를 세 가지 운영 화면에 바로 쓰기 위한 구조다.

1. 매장별 상품을 앱과 저울에 정확히 맞춘다.
2. 레시피와 발주 계산을 안정적으로 유지한다.
3. 사람이 YAML을 봐도 이해할 수 있게 관계를 단순하게 만든다.

핵심 판단:

- `Waterbe`는 기준 원본이다.
- `StoreItem`이 앱 상품, 저울 상품, 매장 판매상품을 연결하는 중심이다.
- 레시피는 상품 정보가 아니라 생산 구성표다.
- 가격, 마트코드, 판매 여부는 매장마다 다르므로 `Item`이 아니라 `StoreItem`에 둔다.

## 현재 구조의 문제

현재 데이터는 실제로 이렇게 쓰이고 있다.

- `Product`: 공통 상품명만 거의 갖고 있다.
- `Recipe`: 매장, 상품, 가격, 마트코드, 재료 구성을 모두 들고 있다.
- `Ingredient`: 내부 재료명이다.
- `PurchaseSpec`: 실제 발주 품목이다.
- `PriceHistory`: 발주 단가 이력이다.

문제는 `Recipe`가 너무 많은 책임을 갖는다는 점이다.

```text
Recipe = 매장상품 + 가격 + 마트코드 + 레시피 + 이력
```

이 구조에서는 앱 데이터, 저울 데이터, 레시피 데이터를 따로 비교하기 어렵다.

## v3 핵심 구조

```text
Store
  매장

Item
  공통 판매상품

StoreItem
  매장별 판매상품
  앱 상품과 저울 상품을 연결하는 중심

BillOfMaterials
  StoreItem 1개를 만들 때 필요한 재료 구성

Material
  내부 자재명

PurchaseItem
  실제 발주 품목/규격

PurchasePrice
  발주 단가 이력
```

## 클래스 설계

### Store

매장이다.

```yaml
- id: wolgye
  class: Store
  data:
    name: 월계점
    branch: 월계
    location: 이마트 월계점 수산코너
    active: true
```

### Item

매장과 무관한 공통 상품이다.

예:

- 낙지전복해물탕
- 문어전복해물탕
- 흰다리새우
- 간장게장

```yaml
- id: item_mk_014
  class: Item
  data:
    name: 낙지전복해물탕
    kind: meal_kit
    salesUnit: 개
    active: true
```

`Item`에는 가격, 마트코드, 매장 정보를 넣지 않는다.

### StoreItem

v3의 중심 클래스다.

특정 매장에서 판매하는 특정 상품이다. 앱, 저울, CL-Works와 연결되는 값도 여기에 둔다.

```yaml
- id: storeitem_wolgye_mk014
  class: StoreItem
  data:
    storeId: wolgye
    itemId: item_mk_014
    displayName: 낙지전복해물탕 (월계)
    martCode: "235905"
    price: 23800
    salesUnit: 개
    active: true
    appProductId: null
    scalePluCode: "235905"
    scaleName: 낙지전복해물탕
    effectiveFrom: "2026-01-01"
    effectiveTo: null
```

필드 의미:

| 필드 | 의미 |
| --- | --- |
| `storeId` | 판매 매장 |
| `itemId` | 공통 상품 |
| `displayName` | 매장별 표시명 |
| `martCode` | 이마트/앱/저울을 맞추는 핵심 코드 |
| `price` | 매장 판매가 |
| `active` | 현재 판매 여부 |
| `appProductId` | 시코드 앱 DB의 상품 ID. 나중에 채운다 |
| `scalePluCode` | 저울/CL-Works 상품 코드. 보통 martCode와 같게 둔다 |
| `scaleName` | 저울에 표시할 상품명 |
| `effectiveFrom/effectiveTo` | 가격/코드/판매조건 이력 |

권장 제약:

- 현재 활성 레코드는 `(storeId, martCode)`가 유일해야 한다.
- 현재 활성 레코드는 `(storeId, itemId)`가 가능하면 유일해야 한다.
- `scalePluCode`는 기본적으로 `martCode`와 같게 둔다.

### BillOfMaterials

제품 구성표다. 기존 `Recipe.uses`를 옮긴다.

```yaml
- id: bom_wolgye_mk014_20260101
  class: BillOfMaterials
  data:
    storeItemId: storeitem_wolgye_mk014
    effectiveFrom: "2026-01-01"
    effectiveTo: null
    lines:
      - materialId: mat_낙지
        quantity: 230
        unit: g
        purchaseItemId: pitem_078
      - materialId: mat_전복
        quantity: 1
        unit: 마리
        purchaseItemId: pitem_022
```

원칙:

- 가격 변경만 있으면 `StoreItem` 이력만 추가한다.
- 재료 구성 변경이면 `BillOfMaterials` 이력을 추가한다.
- 과거 BOM은 덮어쓰지 않는다.

### Material

내부 기준 자재명이다. 원재료, 포장재, 소모품을 모두 포함한다.

```yaml
- id: mat_전복
  class: Material
  data:
    name: 전복
    type: ingredient
    origin: 국내산
    defaultUnit: 마리
    active: true
```

`type` 값:

- `ingredient`
- `packaging`
- `supply`

### PurchaseItem

업체에 실제로 발주하는 품목/규격이다.

```yaml
- id: pitem_022
  class: PurchaseItem
  data:
    materialId: mat_전복
    vendorName: 대영상사
    orderName: 활전복
    orderUnit: 1kg
    category: ingredient
    countPerKg: 20
    packCount: null
    active: true
```

하나의 `Material`에 여러 `PurchaseItem`이 연결될 수 있다.

예:

- 흰다리새우살 대 페루산
- 흰다리새우살 소 베트남산
- 전복 20미
- 전복 25미

### PurchasePrice

발주 단가 이력이다.

```yaml
- id: price_pitem_022_20260101
  class: PurchasePrice
  data:
    purchaseItemId: pitem_022
    date: "2026-01-01"
    unitPrice: 32000
    deliveryFee: null
    memo: null
```

가격 변경 시 기존 레코드를 수정하지 않고 새 레코드를 추가한다.

### ProductionRule

요일별 기본 생산량이다.

```yaml
- id: prod_rule_wolgye_mk014_20260414
  class: ProductionRule
  data:
    storeItemId: storeitem_wolgye_mk014
    dailyQty: {mon: 2, tue: 2, wed: 2, thu: 2, fri: 4, sat: 6, sun: 4}
    unit: 개
    effectiveFrom: "2026-04-14"
    effectiveTo: null
    memo: null
```

기존 `ProductionTemplate`에 해당한다.

### ProductionWeek

주간 생산계획이다.

```yaml
- id: prod_week_wolgye_20260706_mk014
  class: ProductionWeek
  data:
    storeItemId: storeitem_wolgye_mk014
    weekStart: "2026-07-06"
    planned: {mon: 2, tue: 2, wed: 2, thu: 2, fri: 4, sat: 6, sun: 4}
    adjusted: null
    actual: null
    status: planned
```

### StockCount

재고 실사다.

```yaml
- id: stock_wolgye_20260708_mat_전복
  class: StockCount
  data:
    storeId: wolgye
    materialId: mat_전복
    purchaseItemId: pitem_022
    date: "2026-07-08"
    quantity: 12
    unit: 마리
    boxes: null
    openRemainder: 12
    memo: null
```

### PurchaseReceipt

입고 기록이다.

```yaml
- id: receipt_wolgye_20260708_001
  class: PurchaseReceipt
  data:
    storeId: wolgye
    purchaseItemId: pitem_022
    date: "2026-07-08"
    quantity: 2
    unit: 박스
    memo: null
```

### SalesDaily

일별 판매 기록이다.

```yaml
- id: sales_wolgye_20260708_mk014
  class: SalesDaily
  data:
    storeItemId: storeitem_wolgye_mk014
    date: "2026-07-08"
    quantity: 8
    unitPrice: 23800
    amount: 190400
    source: namseon
```

Namseon SQLite는 당분간 별도 유지한다. 필요할 때 v3 조회용 뷰로 변환한다.

## 앱/저울 연동 기준

v3에서는 `StoreItem` 하나가 세 시스템을 연결한다.

```text
Waterbe StoreItem
  storeId
  itemId
  martCode
  price
  appProductId
  scalePluCode

Supabase products_{store}
  mart_code
  waterbe_product_id 또는 waterbe_store_item_id
  retail_price
  is_operating

CL-Works / CAS CL-5200
  PLU 또는 상품코드
  상품명
  가격
```

권장 매칭 우선순위:

1. `waterbe_store_item_id`
2. `storeId + martCode`
3. `storeId + normalizedName`

앱 DB에는 장기적으로 `waterbe_store_item_id`를 추가하는 것이 가장 좋다. `waterbe_product_id`는 공통 상품까지만 가리키므로 매장별 가격/마트코드 차이를 표현하기 부족하다.

## 파일 구조 제안

기존 `instances/master/recipes/{store}.yaml`을 v3에서는 분리한다.

```text
instances/v3/
  master/
    stores.yaml
    items.yaml
    store_items/
      wangsimni.yaml
      mapo.yaml
      wolgye.yaml
    materials.yaml
    purchase_items.yaml
    purchase_prices.yaml
    bom/
      wangsimni.yaml
      mapo.yaml
      wolgye.yaml
  production/
    rules/
      wangsimni.yaml
      mapo.yaml
      wolgye.yaml
    weeks/
      wangsimni.yaml
      mapo.yaml
      wolgye.yaml
  inventory/
    stock_counts/
      wangsimni.yaml
      mapo.yaml
      wolgye.yaml
    purchase_receipts/
      wangsimni.yaml
      mapo.yaml
      wolgye.yaml
  sales/
    daily/
      wangsimni.yaml
      mapo.yaml
      wolgye.yaml
```

처음부터 기존 데이터를 대체하지 않는다. `instances/v3/` 아래에 변환 산출물을 만들고 검증한다.

## 기존 데이터에서 v3로 옮기는 규칙

| 기존 | v3 |
| --- | --- |
| `Product` | `Item` |
| `Recipe.data.price` | `StoreItem.price` |
| `Recipe.data.martCode` | `StoreItem.martCode`, `StoreItem.scalePluCode` |
| `Recipe.relations.forProduct` | `StoreItem.itemId` |
| `Recipe.relations.uses` | `BillOfMaterials.lines` |
| `Ingredient` | `Material(type=ingredient)` |
| `PurchaseSpec` | `PurchaseItem` |
| `PriceHistory` | `PurchasePrice` |
| `ProductionTemplate` | `ProductionRule` |
| `ProductionPlan` | `ProductionWeek` |
| `InventorySnapshot` | `StockCount` |
| `InboundRecord` | `PurchaseReceipt` |
| `SalesRecord` | `SalesDaily` |

## 마이그레이션 순서

1. `Product`를 `Item`으로 변환한다.
2. `Ingredient`를 `Material`로 변환한다.
3. `PurchaseSpec`를 `PurchaseItem`으로 변환한다.
4. `PriceHistory`를 `PurchasePrice`로 변환한다.
5. 매장별 `Recipe`에서 `StoreItem`을 만든다.
6. 매장별 `Recipe.uses`에서 `BillOfMaterials`를 만든다.
7. `ProductionTemplate`을 `ProductionRule`로 변환한다.
8. 기존 발주 계산 결과와 v3 발주 계산 결과를 비교한다.
9. `waterbe-admin`에서 v3 데이터를 읽는 화면을 먼저 만든다.
10. 검증 후 앱 DB에 `waterbe_store_item_id`를 추가한다.

## v3에서 먼저 만들 화면

1. `StoreItem` 목록
   - 매장
   - 상품명
   - 마트코드
   - 가격
   - 앱 상품 연결 상태
   - 저울 코드 연결 상태

2. `BOM` 상세
   - 상품 1개당 재료 구성
   - 발주품목 연결 여부
   - 원산지/규격 표시

3. 앱 비교
   - `StoreItem.martCode` vs `products_{store}.mart_code`
   - 가격 차이
   - 상품명 차이
   - 앱에만 있는 상품
   - Waterbe에만 있는 상품

4. 저울 내보내기
   - 매장 선택
   - 활성 `StoreItem` 목록
   - PLU/마트코드
   - 저울 표시명
   - 가격
   - CSV/XLS 미리보기

## 보류할 것

- 저울 TCP 프로토콜 직접 전송
- CL-Works Pro 자동 조작
- 판매 데이터 완전 통합
- `Vendor` 정규화
- 카테고리 계층 복원

이들은 먼저 `StoreItem`과 `BOM`이 안정된 뒤 진행한다.

## 결론

v3의 중심은 `StoreItem`이다.

기존에는 `Recipe`가 매장상품, 가격, 마트코드, 재료를 모두 들고 있었지만, v3에서는 다음처럼 나눈다.

```text
Item = 공통 상품
StoreItem = 매장별 판매/앱/저울 연결
BillOfMaterials = 생산 재료 구성
Material = 내부 자재
PurchaseItem = 발주 규격
PurchasePrice = 발주 단가
```

이 구조가 되어야 앱 데이터, Waterbe 데이터, 저울 데이터를 안정적으로 연결할 수 있다.
