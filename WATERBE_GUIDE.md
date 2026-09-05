# 워터비 운영 데이터 지침

이 문서는 워터비 업무 지침의 메인 목차다. 실제 규칙은 아래 주제별 문서를 따른다.

## 업무별 지침

| 업무 | 지침 |
| --- | --- |
| 매장, 시코드 운영상품, 상품 ID와 상태 | [매장·상품 지침](docs/guides/STORE_PRODUCTS_GUIDE.md) |
| 재료, 발주규격, 레시피, 가격과 원가 | [레시피·원가 지침](docs/guides/RECIPES_COST_GUIDE.md) |
| 시코드 앱과 CL-5200 저울 연결·상태 검증 | [시코드·저울 연결 지침](docs/guides/SEACODE_SCALE_GUIDE.md) |
| 기본생산량, 주간계획, 조정과 생산실적 | [생산량 지침](docs/guides/PRODUCTION_GUIDE.md) |
| 재고실사와 입고기록 | [재고·입고 지침](docs/guides/INVENTORY_INBOUND_GUIDE.md) |
| YAML 작성, 이력 보존과 검증 | [공통 데이터 작성·검증 지침](docs/guides/DATA_RULES_GUIDE.md) |
| 직원, 근무일정과 텔레그램 권한 | [인사관리 지침](PERSONNEL_GUIDE.md) |
| 매출 조회·동기화 | [매출 지침](instances/sales/README.md) |
| 월계점 일일 생산·할인·폐기 연결 | [월계점 일일 운영 지침](WOLGYE_DAILY_OPERATIONS_GUIDE.md) |

## 기준 정의

클래스, 필드, 관계와 제약조건의 기술적 기준은 [schema.yaml](schema.yaml)을 따른다.

업무 데이터를 변경하기 전에 이 목차에서 해당 업무 지침을 읽고, 여러 영역이 연결된 작업이면 관련 문서를 모두 확인한다.
