# AGENTS.md

Waterbe 업무를 시작할 때 [WATERBE_GUIDE.md](WATERBE_GUIDE.md)에서 해당 업무 지침을 찾아 읽는다.

## 지침 연결

| 작업 | 먼저 읽을 문서 |
| --- | --- |
| 전체 업무 지침 찾기 | [WATERBE_GUIDE.md](WATERBE_GUIDE.md) |
| 상시 워커와 요청형 작업의 실행 장소 | [운영 실행 기준](docs/guides/OPERATING_EXECUTION_GUIDE.md) |
| 씽크패드 중앙 점검·복구·코덱스 관리 | [중앙 관리 지침](docs/guides/THINKPAD_CENTRAL_MANAGEMENT_GUIDE.md) |
| 출처별 데이터 워커 책임·저장 계약 | [데이터 워커 구성](docs/guides/PROGRAM_RESPONSIBILITIES_GUIDE.md#데이터-워커-구성--출처별-관리) |
| 에이전트 공통 API 발견·사용 | [API 사용 입구](docs/guides/PROGRAM_RESPONSIBILITIES_GUIDE.md#에이전트-공통-api-진입점) |
| 프로그램 구성·프로젝트별 책임 | [프로그램 역할 지침](docs/guides/PROGRAM_RESPONSIBILITIES_GUIDE.md) |
| 매장 생산·저울누계·할인·매출 종합 조회 | [통합 운영 조회 지침](docs/guides/DAILY_STORE_REPORT_GUIDE.md) |
| 매장과 시코드 운영상품 | [매장·상품 지침](docs/guides/STORE_PRODUCTS_GUIDE.md) |
| 문어행사팀 신규 등록·연결 | [문어행사팀 추가 작업](docs/plans/MOONER_ONBOARDING.md) |
| 재료, 레시피와 원가 | [레시피·원가 지침](docs/guides/RECIPES_COST_GUIDE.md) |
| 시코드 앱과 CL-5200 저울 | [시코드·저울 연결 지침](docs/guides/SEACODE_SCALE_GUIDE.md) |
| 품질검사·다이버시점검과 원라벨 확인 | [품질관리솔루션 운영 지침](docs/guides/QUALITY_COMPLIANCE_GUIDE.md) |
| 품질점검 워커 구성(기획·미구현) | [품질점검 워커 지침](docs/guides/QUALITY_CHECK_WORKER_GUIDE.md) |
| 생산량과 생산실적 | [생산량 지침](docs/guides/PRODUCTION_GUIDE.md) |
| 재고와 입고 | [재고·입고 지침](docs/guides/INVENTORY_INBOUND_GUIDE.md) |
| YAML 작성과 검증 | [공통 데이터 작성·검증 지침](docs/guides/DATA_RULES_GUIDE.md) |
| 직원과 일정 | [PERSONNEL_GUIDE.md](PERSONNEL_GUIDE.md) |
| 매출 조회와 동기화 | [instances/sales/README.md](instances/sales/README.md) |
| 월계점 일일 운영기록 | [WOLGYE_DAILY_OPERATIONS_GUIDE.md](WOLGYE_DAILY_OPERATIONS_GUIDE.md) |
| 클래스, 필드와 제약조건 | [schema.yaml](schema.yaml) |

## 공통 원칙

- 업무를 시작할 때 해당 기준이 지침에 있는지 먼저 확인한다. 지침에 없는 기준을
  채팅 기억이나 추정으로 기존 합의처럼 적용하지 않는다. 지침 부재·충돌 시
  [지침 관리 기준](docs/guides/GUIDE_MAINTENANCE_GUIDE.md#지침-유무와-판단-기준)을 따른다.

- 활성 중앙 워커는 모두 씽크패드에서 실행한다. Windows 예약 작업을 다시 켜거나
  Windows 정지본 DB를 최신 원본으로 쓰지 않는다. 현재 상태/경로/보류 범위는
  [중앙 이전 기록](docs/plans/THINKPAD_CENTRAL_MIGRATION.md)과 공통 접속 지침을 따른다.
  이는 현재 상시 통신·수집 워커의 실행 기준일 뿐 업무별 호스트 제한이 아니다.
  개발·점검·매출 동기화·OCR·검산은 양쪽 모두 가능하며 환경·성능·접속에 따라
  선택한다. [운영 실행 기준](docs/guides/OPERATING_EXECUTION_GUIDE.md)을 따른다.

- 씽크패드 원격 실행·파일 전송은 [씽크패드 공통 접속](docs/guides/THINKPAD_CONNECTION_GUIDE.md)을 따른다. 두 호스트의 파일과 실행 주체를 구별한다.

- 변경·장애 원인 조사는 [운영 기록·추적 지침](docs/guides/OPERATION_HISTORY_GUIDE.md)을 따른다. 채팅 기억 대신 원본·사건 이력·확인 시각을 대조하며 미연결 기록과 구현/배포 상태를 구별한다.
- 새 기능은 담당 원본·공통 사건 ID·성공 증거·중앙 기록 연결·감시 불가 범위를 함께 명시한다. 기존 기록 경로를 재사용하고 비밀/원시 오류를 공통 이력에 넣지 않는다. `history.status`가 오래됐으면 현재 정상으로 보고하지 않는다.

- 생산량·할인·매출 조회는 [통합 운영 조회 지침의 조회 완료 조건](docs/guides/DAILY_STORE_REPORT_GUIDE.md#조회-완료-조건--답변-전-필수)을 반드시 통과한 뒤 답한다. 원본 미조회 상태에서 기록 없음·0을 단정하거나 기본계획으로 대신 답하지 않는다.

- 사용자의 요청 범위만 변경한다.
- 삭제, 이름 변경 또는 기록 재작성은 사용자가 명시적으로 요청하지 않았다면 먼저 확인한다.
- 여러 업무영역이 연결된 작업은 관련 지침을 모두 읽고 처리한다.

## 하위 에이전트 모델 사용

- 사용자가 하위 에이전트 위임을 요청한 경우에만 위임한다.
- 단순 조회·파일 탐색·요약은 `gpt-6-luna`의 `low`를 사용한다.
- 일반적인 코드 수정·테스트·Git 작업은 `gpt-5.6-terra`의 `low`를 사용한다.
- 조금 복잡한 분석·수정은 `gpt-5.6-terra`의 `high`를 사용한다.
- 하위 에이전트에는 Sol 또는 Astra 모델을 사용하지 않는다.
- 불필요한 다중 에이전트 실행과 같은 내용의 중복 조사를 피한다.
