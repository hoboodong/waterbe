# 생산량 지침

매장별 생산상품과 생산량을 기록하는 규칙을 정의한다.

## 처리 원칙

- 시코드 앱의 운영 중 상품을 기본으로 확인한다.
- 시코드 기본상품 외에 사용자가 말한 예외적이거나 추가적인 생산상품도 포함한다.
- 완제품은 실제 생산 개수로 기록한다.
- 원물은 투입 수량과 단위를 기록한다.
- 실제 완제품 수량을 모를 때만 추정치로 기록한다.
- 사용자가 매장과 생산내용을 말하면 상품 확인 후 매장·날짜별 생산기록으로 저장한다.
- 별도의 제외상품 규칙은 두지 않는다.

## ProductionTemplate

`instances/production/templates/{store}.yaml`에 매장·상품·요일별 기본 생산량을 보관한다.

- `dailyQty`: `mon`부터 `sun`까지 요일별 기본량
- `unit`: 개, 팩, kg 등 생산단위
- `effectiveFrom`, `effectiveTo`: 적용기간
- `memo`: 변경 근거

변경 시 기존 활성 레코드의 `effectiveTo`를 새 적용일 전날로 닫고 새 레코드를 추가한다.

## ProductionPlan

`instances/production/{store}.yaml`에 상품별 주간 생산계획을 기록한다.

- `weekStart`: 월요일 날짜
- `dailyPlan`: 생성 시점의 기본량 복사본이며 수정 금지
- `dailyAdjusted`: 이후 조정된 요일만 기록
- `dailyActual`: 실제 생산량
- `status`: `planned`, `in_progress`, `completed`

유효 계획량은 조정값이 있으면 `dailyAdjusted[day]`, 없으면 `dailyPlan[day]`다.

## 원물과 완제품

- 원물 투입량과 완제품 생산량을 구분한다.
- 실제 완성수량이 있으면 `actualOutputQty`를 우선한다.
- 실제값이 없을 때만 `estimatedOutputQty`와 `outputQtyApproximate: true`를 사용한다.
- 추정값은 실제값과 구분한다.

| 품목 | 원물 기준 | 추정 기준 |
| --- | --- | --- |
| 흰다리새우 | 1팩 = 2kg | 약 315g/팩 |
| 손질낙지 | 1박스 = 6kg | 300g/팩 기준 약 20팩 |
| 작은 흰다리새우살 | 완제품 기준 | 약 230g/팩 |

환산값은 추정치이며 실제 포장수량 또는 중량 확인 후 확정한다.
