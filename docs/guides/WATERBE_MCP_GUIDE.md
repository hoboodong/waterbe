# 워터비 MCP — 업무 지침과 실행 입구

## 목적과 범위

사용자가 요청하면 어느 연결된 AI든 같은 지침·기능 목록·원본 조회 방법을 사용한다.
서버는 씽크패드에서 실행하고 Windows는 기존 SSH로 연결한다. 별도 HTTP 공개 주소나
AI 모델·무인 작업·감시 스케줄을 추가하지 않는다. 접속할 때 STDIO 서버가 시작된다.

원본 지침은 AGENTS.md → WATERBE_GUIDE.md → 담당 지침이다. 기능 등록 원본은
config/api_catalog.json, 실행 원본은 scripts/waterbe_api.py다. MCP는 이를 재사용한다.
운영 장소·기존 인증·원본의 소유권은 [운영 실행 기준](OPERATING_EXECUTION_GUIDE.md)과
[프로그램 역할](PROGRAM_RESPONSIBILITIES_GUIDE.md)을 따른다.

## 업무 순서

1. `waterbe_start`로 설치 코드와 문서 버전, 실행 가능 범위를 확인한다.
2. `waterbe_find_guides(query)`와 `waterbe_list_operations(query)`로 업무를 찾는다.
3. `waterbe_describe_operation(operation)`의 담당 지침을 `waterbe_read_guide(path)`로
   읽는다. has_more면 next_line부터 끝까지 읽고 서로 다른 hash의 조각은 섞지 않는다.
4. mcp_callable=true 기능의 `mcp_tool`을 확인한다. 기본 조회는 `waterbe_call`,
   확장 기존 기능은 `waterbe_prepare_action` 후 `waterbe_submit_action`으로 실행한다.
   `waterbe_action_status`로 같은 ID의 결과를 확인한다. planned는 구현을 꾸며 호출하지
   않고 담당 지침의 기존 수동 업무 절차를 사용한다.
5. 결과의 출처·자료 확인 시각·경고·누락을 확인한다. 접속 성공/조회 성공은 현재
   업무 정상이나 물리 저울 확인을 의미하지 않는다. unavailable을 0으로 대신하지 않는다.

기본 조회5개 외 기존 native 기능을 연결했다. 원본 기능을 다시 구현하지 않고 기존
저울 요청 RPC/작업함/실행기, CASPi 프로토콜·게시 검증, 매출 적재기와 중앙 관리기를
호출한다. 재고·레시피 변경·인사·통합 계산의 새 공통 API는 여전히 기획 상태다.
MCP 연결 완료는 해당 기능을 사용할 수 있다는 뜻이며 임의 업무 변경의 승인이 아니다.

## 기존 기능 실행 (2026-10-21 확장)

| 업무 | 실행 ID |
| --- | --- |
| 앱 상품·할인 출력·작동 진단 | products.read / discounts.read / diagnostics.read |
| 저울 저장 상품·문구·공용 작업 상태 | scale.products.read / scale.texts.read / scale.work.read |
| CASPi 실제 상품·문구·일누계 | scale.product.read / scale.text.read / scale.day.read |
| 누계 새 수집 | scale.collect |
| 상품/문구 변경 및 원 작업 읽기 재확인 | scale.product.change / scale.text.change / scale.reconcile |
| 저장 레시피 점검·사건 추가 | recipes.audit / history.append |
| 남선/대영 월조회·동기화·대영 OCR | sales.namseon.month / sales.daeyoung.month / sales.namseon.sync / sales.daeyoung.sync / sales.daeyoung.ocr |
| 중앙 점검·승인 재시작·기존 백업 | central.check / central.restart / central.backup |

1. describe_operation의 required_parameters/optional_parameters/parameter_rules와 담당
   지침을 읽는다. 미리보기는 prepare_action(operation,parameters)이며 실행하지 않는다.
2. 실제 사용자 요청 범위에서 submit_action(operation,parameters,operation_id,user_request).
   operation_id는 새 작업에 한 번 정한 UUID, user_request는 비밀 없는 짧은 요청 요약이다.
   요약/플래그는 사용자 승인이나 OS 인증을 대신하지 않는다. 이미 받은 명확한 요청을
   불필요하게 다시 승인받을 필요는 없지만, 요청에 없는 변경을 실행하면 안 된다.
3. 작업은 중앙 보호 DB ~/.local/state/waterbe-mcp/actions.db에 먼저 보존한다.
   별도 요청형 프로세스가 실행하므로 MCP 재접속 후에도 같은 ID로 결과를 읽는다.
   같은 ID·같은 내용은 재실행하지 않고, 다른 내용은 충돌로 보존한다.
4. pending/running/finished는 MCP 작업 단계다. 내부 result.status와 실행 원본의
   실제 ACK/재읽기/게시 증거를 보고한다. accepted는 저울 적용이 아니다.
   프로세스 종료나 native exit0도 업무 완료 증거를 대신하지 않는다.
5. 실행 도중 프로세스 소실/응답 유실은 execution_unknown으로 남긴다. 임의 새 ID
   쓰기·자동 재실행은 하지 않는다. 기존 저울 작업 ID/영수증/재확인 기능으로 조사한다.
   다른 대상의 작업은 계속 가능하다. 매출 동기화가 이미 실행 중이면 중복 시작하지 않는다.
6. 저울 쓰기는 기존 상품/문구 요청 RPC만 호출한다. 상품 expected_fields와 snapshot
   SHA256, 문구 expected_presence/content를 필수로 지키며 기존 워커가 CASPi에 전달한다.
   status 조회가 해당 큐 결과를 다시 읽는다. direct scale write/V1 우회/기대값 생략 없음.
7. CASPi 읽기·누계·재확인은 설치된 중앙 전송/영수증 검증·게시 입구를 재사용한다.
   앱의 Bluetooth 우선 연결 규칙이나 기존 앱 버전은 바꾸지 않는다.
8. 남선 날짜 지정 sync는 기존 SQLite→수파 날짜 적재다. 날짜 없는 sync는 기존 전체
   Drive 정리/중복 휴지통/적재/업로드를 포함하므로 전체 동기화 요청 때만 사용한다.
   대영 sync는 기존 검증 결과 디렉터리를 받는다. OCR은 별도이며 검증·적재와 다르다.
9. 실행 증거는 로컬 작업 DB에 보존하고 기존 공통 이력/전달 큐에 같은 operation_id로
   연결한다. 이력 실패는 원 작업을 다시 실행하지 않는다. 원시 오류·비밀을 응답하지 않는다.
10. check_connections는 기존 실행기/설정 존재와 REST RPC 발견만 점검한다.
    실제 저울 쓰기나 매출 적재 시험으로 해석하지 않는다.

## 입력·결과

- 매출: business_date=YYYY-MM-DD 필수. 원본 행/버전과 누락을 반환하며 통합 계산과 다르다.
- 이력: 날짜 또는 operation_id를 필수로 지정한다. store/feature/source/target/result로
  더 좁힌다. limit 기본100, 최대500, after 기본0. has_more면 next_after로 이어 읽는다.
  페이지 뒤의 자료를 이미 모두 조회한 것처럼 보고하지 않는다.
- 지침: 등록된 Markdown만 읽는다. 임의 파일/환경변수/비밀 설정/SQL/셸 실행 도구는 없다.
- resources: waterbe://start, waterbe://catalog, waterbe://guides,
  waterbe://guide/<URL-encoded 상대경로>. prompt: waterbe_task(task).
- 수파 인증은 씽크패드 기존 central.env를 실행 환경에만 로드한다. Windows로 복사하지 않는다.

## 설치와 연결

- SDK: `config/mcp-runtime-requirements.txt`의 mcp==2.3.0을 별도 venv에 설치한다.
  기존 중앙 워커의 Python 환경은 변경하지 않는다.
- 중앙 소스/launcher: `scripts/waterbe_mcp.py`, `scripts/install_waterbe_mcp.py`.
  버전별 소스 hash와 설치 증거를 보존하고 ~/.local/bin/waterbe-mcp로 실행한다.
- 씽크패드 Codex: `codex mcp add waterbe -- /home/sdg/.local/bin/waterbe-mcp`.
- Windows Codex: `codex mcp add waterbe -- "C:/Program Files/Git/usr/bin/ssh.exe" -T -o BatchMode=yes -o ConnectTimeout=8 thinkpad /home/sdg/.local/bin/waterbe-mcp`.
  Windows OpenSSH는 SDK 비동기 파이프 연결에서 종료되는 현상이 확인되어 Git SSH를 사용한다.
- 등록 후 `python scripts/configure_waterbe_mcp_timeouts.py`로 waterbe 항목만 제한 시간을 맞춘다.
- 기존 Codex 설정을 백업하고 waterbe 항목만 추가한다. 모델·로그인·다른 MCP·tmux 대화를
  변경하지 않는다. 시작 제한30초, 도구 제한180초. 해당 PC의 기존 SSH 권한을 사용한다.
- 이미 열린 AI 대화는 도구 목록 새로고침/클라이언트 재시작이 필요할 수 있다.
  설정 등록·SDK handshake·현재 대화 도구 노출을 각각 구별해 기록한다.

## 검증과 운영 기록

로컬 단위 검사와 공식 SDK STDIO 검증으로 initialize, tools/list, resources/list,
prompts/list, 지침 읽기와 실행 기능 검증을 수행한다. 원격은 Windows→SSH→중앙과
씽크패드 현지 연결을 각각 확인한다. 실제 history.status/read 또는 날짜를 지정한
매출 조회의 반환 상태까지 확인하며 물리 쓰기/수집/재시작 시험은 실행하지 않는다.

설치 증거는 ~/.local/state/waterbe-mcp에 코드 hash·SDK 버전·시각·검증 결과를 보존한다.
공통 운영 이력에는 같은 배포 사건 ID로 설치/조회 검증 근거를 연결한다.
SSH 또는 중앙 정지 시 MCP는 접속 실패로 남으며 데이터 워커는 독립 동작한다.
연결 실패로 쓰기를 재실행하거나 기존 요청을 새 ID로 만들지 않는다.

변경 후 담당 지침·카탈로그·도구·회귀 검사를 같이 갱신한다. MCP는 정해진
권한과 업무 규칙을 전달하며 사용자 요청이나 실제 인증을 대신하지 않는다.
