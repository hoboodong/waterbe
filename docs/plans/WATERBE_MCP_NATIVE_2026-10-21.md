# MCP 기존 기능 연결·운영 검증 — 2026-10-21

공통 사건: `waterbe-mcp-native-20261021`. 서버 버전2026.10.21.2.
기본5개 및 native24개, 총29개 실행 입구를 연결했다.
상세 계약·입력·실패 처리는 [MCP 지침](../guides/WATERBE_MCP_GUIDE.md)을 따른다.

## 구현·설치

- Waterbe 구현3712a29, 보완078cdcc/1466cc4/e49a24e.
- 중앙 불변 실행본 `/home/sdg/.local/lib/waterbe-mcp-3f7aadeae7619958`.
- 양쪽 Codex 기존 waterbe 연결을 유지. 사용자 서비스 bus를 준비해 현지 MCP의
  central.check도 실행 가능하게 했다. 자격증명을 Windows로 복제하지 않았다.
- 요청형 action을 중앙 SQLite에 먼저 저장하고 동일 UUID 재호출은 조회로 처리한다.
  접수/프로세스 종료/저울 검증/서버 게시를 구별한다. 연결 종료 뒤에도 원 작업 유지.
- 쓰기는 기존 상품·문구 RPC, CASPi 읽기·누계·재확인은 기존 중앙 전송/게시 검증,
  매출은 기존 적재기/원본 정리 절차, 관리/백업은 기존 central launcher를 호출한다.
- 기존 공통 이력 delivery 큐 재사용. publication 실패는 원 영수증을 보존하며
  쓰기를 다시 실행하지 않는다. 원시 오류는 공통 이력/응답에 넣지 않는다.

## 검증

- Windows·씽크패드 단위/회귀34개 통과.
- 양쪽 실제 STDIO, 도구10개/리소스/프롬프트, 기존 이력 조회 성공.
- 앱 상품·할인출력·진단·저울 저장 상품/문구·공용 작업함·레시피 점검·중앙 점검·
  CASPi 일누계의 native 읽기 확인. 저장값 조회를 물리 저울 최신값으로 대신하지 않았다.
- 네 매장 실제 일누계: 미아1.83초, 마포2.02초, 월계1.69초, 왕십리1.98초.
  이는 2026-10-20 일누계 한 페이지와 게시까지의 관측이며 모든 요청의 속도 보장은 아니다.
- 미아 실제 상품/광고문구 읽기 BCC 검증 및 원 작업 영수증 조회 성공.
- 작업89672705-e6d7-44a3-8a7f-44583c0b4e16의 공통 수파 이력2행 확인.
- 기존 상품/문구 변경 RPC를 현재 서비스 권한의 REST 스키마에서 발견했다.
  새 임의 상품 쓰기·매출 적재·재시작·OCR 대량 실행은 하지 않았다.
  이런 기능은 입력·기존 실행 경로·회귀 검증이며 실제 업무 성공은 다음 요청의
  원 작업 ACK/readback/게시·저장 합계로 별도 판정한다.

증거는 중앙 `~/.local/state/waterbe-mcp/verified-native-central-20261021.json`,
`verified-native-windows-20261021.json`, `verified-devices-20261021.json`과 actions.db.
이전에 열린 대화의 도구 목록 갱신은 별도다. 새 연결은 설치된 launcher를 사용한다.

## 발견한 CASPi 초기화 병목 보완

CLI 진입 시 OperationStore가 모든 기존 receipt payload를 다시 backfill하려 하며
미아에서 OperationalError/긴 초기화가 관측됐다. 누락 ID를 인덱스로 먼저 조회하고,
실제 누락된 완료 영수증만 backfill하게 변경했다. 기존 ID/내용/검증/격리는 유지했다.

- CAS source commit `0ee77e256c01ad4d03345570959629c1dfc89db0` origin/main 게시.
  과거/미커밋 작업본은 reset/merge하지 않고 보존했다. 최신 원격 기준에 이번 변경만
  담은 커밋이며 기존 개발 변경을 편의상 포함하지 않았다.
- 초기화2/Bluetooth20 검사 통과. Waterbe 설치 patch2도 회귀34개에 포함.
- 네 매장 설치 hash `118706a3…` → `8cba69f6…`.
- 백업 `/var/backups/caspi-ledger-probe/20261021T025122Z` 미아,
  `T025157Z` 마포, `T025159Z` 월계, `T025201Z` 왕십리.
- 중앙 CAS canonical source에도 같은 블록만 적용, 원본 백업 보존.
  DB 재작성/서비스 재시작/네트워크 변경/저울 값 변경 없음. 문어팀 미변경.

## 미구현/미확인 구별

operations.report/inventory.manage/recipes.manage/personnel.manage는 새 공통 API가
기획 상태다. 기존 수동 업무를 금지하지 않고 해당 지침으로 수행하며 가상 API를 만들지 않는다.
중앙 Supabase CLI가 없으므로 DB 내부 통계/I/O 예산 점검은 여전히 미확인이다.
REST 조회 성공으로 이를 정상이라고 주장하지 않는다. 폰 오프라인 미게시 상태와 실제
휴대폰 쓰기 성공, 중앙 모든 워커의 업무 건강도 이번 MCP 연결 완료와 별개다.
