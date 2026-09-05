# 재고·입고 지침

매장별 재고실사와 입고기록의 작성 규칙을 정의한다.

## InventorySnapshot

- 위치: `instances/inventory/{store}.yaml`
- 실사일마다 새 레코드를 추가하고 과거 기록을 덮어쓰지 않는다.
- `date`, `quantity`, `unit`, `memo`, 재료와 매장 관계를 기록한다.
- ID는 `snap_{매장약어}_{YYYYMMDD}_{재료약어}` 형식을 따른다.

## InboundRecord

- 위치: `instances/inventory/inbound/{store}.yaml`
- 입고 건마다 새 레코드를 추가한다.
- 수량은 발주단위 기준이며 실제 단위를 명시한다.
- 기존 발주규격과 매장을 참조한다.
- ID는 `inbound_{매장약어}_{YYYYMMDD}_{순번}` 형식을 따른다.

## 생산과 연결

- 권장 생산량에는 최근 실사와 이후 입고·사용량을 반영한다.
- 원물 재고와 완제품 재고를 섞지 않는다.
- 단위가 다르면 발주규격과 레시피 기준으로 환산한다.
- 추정재고와 실사재고를 구분하고 실사값을 우선한다.
