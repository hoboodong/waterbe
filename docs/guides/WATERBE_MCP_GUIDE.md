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
4. mcp_callable=true인 기능은 `waterbe_call`로 실행한다. native는 담당 프로그램의
   기존 입구는 있지만 MCP 실행은 미연결이고, planned는 미구현이다.
5. 결과의 출처·자료 확인 시각·경고·누락을 확인한다. 접속 성공/조회 성공은 현재
   업무 정상이나 물리 저울 확인을 의미하지 않는다. unavailable을 0으로 대신하지 않는다.

현재 MCP 실행 기능: system.check, history.read, history.status,
sales.namseon.read, sales.daeyoung.read. 저울 변경·동기화·재고·레시피 등은
목록과 담당 지침에서 발견할 수 있지만 새 MCP 실행 어댑터가 연결된 것은 아니다.
이 목록을 기능 구현 완료로 해석하지 않는다.

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
- Windows Codex: `codex mcp add waterbe -- ssh -T -o BatchMode=yes -o ConnectTimeout=8 thinkpad /home/sdg/.local/bin/waterbe-mcp`.
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
