# Waterbe Ontology Redesign Draft

## 목표

현재 스키마는 온톨로지 표현은 풍부하지만 실제 데이터는 훨씬 단순하다. v3의 목표는 운영자가 매일 쓰는 장부 구조를 중심에 두고, 계산에 꼭 필요한 관계만 남기는 것이다.

## 현재 데이터에서 보이는 문제

- `Product`는 대부분 `name`만 갖고 있다. `unit`, `price`, `soldAt`, `belongsTo`는 스키마에는 있지만 실제 데이터에는 거의 없다.
- `Recipe`가 판매가, 마트코드, 상품-매장 연결, 원재료 사용량을 동시에 담당한다.
- `PurchaseSpec`는 발주 품목, 포장재, 소모품을 모두 담고 있지만 `Vendor` 클래스는 구현되지 않았다.
- `Ingredient` 스키마는 원산지, 손실률, 태그 등 많은 필드를 정의하지만 실제 데이터는 `name`, 일부 `origin`만 쓴다.
- 스키마와 가이드가 어긋난다. 예: `PurchaseSpec.unitG`, `PriceHistory.vendor/memo`, `Schedule.type`.
- 운영 데이터는 `InventorySnapshot`, `InboundRecord`, `ProductionTemplate`, `ProductionPlan`, `SalesRecord`로 나뉘어 있지만 실제로 채워진 것은 일부 매장에 치우쳐 있다.

## v3 설계 원칙

1. 기준 데이터와 장부 데이터를 분리한다.
2. `relations`를 줄이고, 사람이 자주 보는 ID 참조는 필드처럼 평평하게 둔다.
3. 이력은 별도 레코드로만 추가한다. 과거 레코드 덮어쓰기는 금지한다.
4. 매장별 차이는 `StoreItem`에서 관리한다. 상품 자체에는 매장 가격이나 마트코드를 넣지 않는다.
5. 발주 계산에 필요한 최소 필드만 필수로 둔다.

## 핵심 클래스

### 기준 데이터

| v3 클래스 | 역할 | 기존 대응 |
| --- | --- | --- |
| `Store` | 매장 | `Store` |
| `Item` | 판매 상품의 공통 이름 | `Product` |
| `StoreItem` | 매장별 판매상품, 가격, 마트코드, 판매여부 | `Product` + `Recipe.price` + `Recipe.martCode` + `soldAt` |
| `Material` | 원재료/포장재/소모품의 내부 기준명 | `Ingredient` |
| `PurchaseItem` | 업체 발주 단위 | `PurchaseSpec` |
| `PurchasePrice` | 발주 단가 이력 | `PriceHistory` |
| `BillOfMaterials` | 상품 1개를 만들 때 필요한 재료 구성 | `Recipe.uses` |

### 운영 장부

| v3 클래스 | 역할 | 기존 대응 |
| --- | --- | --- |
| `ProductionRule` | 요일별 기본 생산량 | `ProductionTemplate` |
| `ProductionWeek` | 주간 생산계획/조정/실적 | `ProductionPlan` |
| `StockCount` | 재고 실사 | `InventorySnapshot` |
| `PurchaseReceipt` | 입고 기록 | `InboundRecord` |
| `SalesDaily` | 일별 판매 수량/금액 | `SalesRecord` 또는 Namseon DB |
| `Staff` | 직원/권한 | `Staff` |
| `CalendarEvent` | 일정 | `Schedule` |

## 가장 큰 구조 변경

### 1. Product와 Recipe를 분리하지 않고 StoreItem + BOM으로 재정의

현재 `Recipe`는 상품의 매장별 판매 정보까지 갖고 있다. v3에서는 다음처럼 나눈다.

- `Item`: "낙지전복해물탕" 같은 공통 상품명
- `StoreItem`: 월계점에서 판매하는 "낙지전복해물탕", 가격 23800원, 마트코드 235905
- `BillOfMaterials`: 해당 `StoreItem` 1개 생산에 필요한 재료 목록

이렇게 하면 가격 변경, 마트코드 변경, 레시피 변경의 책임이 분리된다.

### 2. Ingredient와 PurchaseSpec을 Material + PurchaseItem으로 단순화

`Material`은 내부에서 쓰는 재료 이름이고, `PurchaseItem`은 실제 발주명/단위다.

예:

- `Material`: 흰다리새우살
- `PurchaseItem`: PDTO새우살26-30P(페루산), 9kg, countPerKg 28
- `PurchasePrice`: 2026-01-01 기준 00원

포장재와 소모품도 `Material.type: packaging|supply`로 처리하고, 별도 클래스는 만들지 않는다.

### 3. relations를 줄이고 참조 필드를 명시

기존:

```yaml
relations:
  forProduct: prod_mk_014
  atStore: store_wolgye
```

v3:

```yaml
data:
  storeId: store_wolgye
  itemId: item_mk_014
```

YAML에서 사람이 읽고 수정할 때는 이 편이 단순하다. 그래프 질의가 필요하면 변환 스크립트에서 관계로 해석하면 된다.

## 이행 전략

1. `schema_v3_draft.yaml`을 기준으로 새 구조를 확정한다.
2. 기존 데이터를 읽어 v3 형태로 변환하는 `scripts/migrate_to_v3.py`를 만든다.
3. 기존 `schema.yaml`과 `instances/`는 당분간 유지한다.
4. `calc_order.py`를 v3 구조에서 읽게 만든 뒤 발주 계산 결과가 기존과 같은지 비교한다.
5. 검증 후 `WATERBE_GUIDE.md`를 v3 기준으로 줄인다.

## 보류할 것

- `Category` 계층: 실제 4개 레코드뿐이고 운영 계산에 직접 쓰이지 않는다. v3에서는 `Item.kind` 정도로 충분하다.
- `Vendor` 클래스: 현재 구현되지 않았다. 필요한 경우 `PurchaseItem.vendorName` 문자열로 먼저 둔다.
- `Ingredient` 손실률: 실제 데이터에 거의 없으므로 선택 필드로만 둔다.
- 판매 데이터 통합: Namseon DB가 별도 워크스페이스이므로 YAML 판매 장부와 억지로 합치지 않는다.
