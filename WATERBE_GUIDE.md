# 워터비 운영 데이터 지침

이 문서는 워터비 업무 지침의 메인 목차다. 실제 규칙은 아래 주제별 문서를 따른다.

## 업무별 지침

- 씽크패드 원격 실행·파일 전송: [씽크패드 공통 접속](docs/guides/THINKPAD_CONNECTION_GUIDE.md).

| 업무 | 지침 |
| --- | --- |
| 프로그램 구성·프로젝트별 책임·구현 상태 | [프로그램 역할 지침](docs/guides/PROGRAM_RESPONSIBILITIES_GUIDE.md) |
| 전체 변경·오류·배포 이력 및 채팅 없는 원인 추적 | [운영 기록·추적 지침](docs/guides/OPERATION_HISTORY_GUIDE.md) |
| 에이전트 공통 API 목록·호출·권한·미구현 구분 | [API 사용 입구](docs/guides/PROGRAM_RESPONSIBILITIES_GUIDE.md#에이전트-공통-api-진입점) |
| 라즈·할인·남선·대영 출처별 데이터 워커 구성 | [데이터 워커 구성](docs/guides/PROGRAM_RESPONSIBILITIES_GUIDE.md#데이터-워커-구성--출처별-관리) |
| 매장 생산량·저울누계·할인·폐기·매출 종합 조회 | [통합 운영 조회 지침](docs/guides/DAILY_STORE_REPORT_GUIDE.md) |
| 매장, 시코드 운영상품, 상품 ID와 상태 | [매장·상품 지침](docs/guides/STORE_PRODUCTS_GUIDE.md) |
| 문어행사팀 신규 등록·연결·진행 상태 | [문어행사팀 추가 작업](docs/plans/MOONER_ONBOARDING.md) |
| 재료, 발주규격, 레시피, 가격과 원가 | [레시피·원가 지침](docs/guides/RECIPES_COST_GUIDE.md) |
| 시코드 앱과 CL-5200 저울 연결·상태 검증 | [시코드·저울 연결 지침](docs/guides/SEACODE_SCALE_GUIDE.md) |
| 품질검사·다이버시점검·대표품질·상품라벨·원라벨 대조 | [품질관리솔루션 운영 지침](docs/guides/QUALITY_COMPLIANCE_GUIDE.md) |
| 실제 생산량, 현장 신고와 날짜별 운영기록 | [생산량 지침](docs/guides/PRODUCTION_GUIDE.md) |
| 재고실사와 입고기록 | [재고·입고 지침](docs/guides/INVENTORY_INBOUND_GUIDE.md) |
| YAML 작성, 이력 보존과 검증 | [공통 데이터 작성·검증 지침](docs/guides/DATA_RULES_GUIDE.md) |
| 직원, 근무일정과 텔레그램 권한 | [인사관리 지침](PERSONNEL_GUIDE.md) |
| 매출 조회·동기화 | [매출 지침](instances/sales/README.md) |
| 월계점 일일 생산·할인·폐기 연결 | [월계점 일일 운영 지침](WOLGYE_DAILY_OPERATIONS_GUIDE.md) |

## 개발 기획안

- [통합 운영 조회 기획안](docs/plans/INTEGRATED_OPERATIONS_QUERY_PLAN.md): 워터비·시코드·카스씨엘 역할과 단계별 구현안. 아직 구현·배포된 기능이 아니며 운영 조회 지침을 대체하지 않는다.
- [CASPi·시코드 사건 증명 및 무중단 복구 기획안](docs/plans/CASPI_SEACODE_EVENT_PROOF_PLAN.md): 현장 Bluetooth 실행, 휴대폰/Pi 이중 인터넷 경로, 동일 영수증 병합, PLU별 격리와 재조회 해제 기준.

## 사업 기준·아카이브

| 구분 | 문서 |
| --- | --- |
| 합의된 사업 기준(진행 중) | [BUSINESS_CANON](docs/guides/BUSINESS_CANON.md) |
| 재작성 전 구 가이드·온톨로지 초안 | [archive: 2026-09-pre-rewrite](docs/archive/2026-09-pre-rewrite/) |

## 기준 정의

클래스, 필드, 관계와 제약조건의 기술적 기준은 [schema.yaml](schema.yaml)을 따른다.

업무 데이터를 변경하기 전에 이 목차에서 해당 업무 지침을 읽고, 여러 영역이 연결된 작업이면 관련 문서를 모두 확인한다.
