# 워터비 MCP 설치·검증 — 2026-10-21

- 공통 사건: `waterbe-mcp-20261021-v1`.
- 서버: 씽크패드 `/home/sdg/.local/bin/waterbe-mcp`, 요청 시 STDIO 실행.
- 코드: `63f5ca9`, 연결 검증 보완 `98cb3d5`. 서버 버전 `2026.10.21.1`.
- 고정 실행본: `/home/sdg/.local/lib/waterbe-mcp-ac47b45b82705ea2`.
- 별도 SDK 환경: `/home/sdg/.local/opt/waterbe-mcp-venv`, `mcp==2.3.0`.
- Windows·씽크패드 Codex 모두 `waterbe` 등록. 기존 설정 백업, 다른 서버·모델 설정 보존.
- 시작 제한30초, 도구 제한180초. Windows는 Git SSH 사용.

## 확인한 증거

- 양쪽 단위·회귀 테스트22개 통과.
- 양쪽 실제 STDIO handshake, 도구6개·정적 리소스3개·프롬프트1개 조회 통과.
- 지침 검색·읽기, 미연결 저울 쓰기 실행 거절 확인.
- 양쪽 실제 `history.status` 조회 성공1행, 2026-10-20 deployment 이력2행 확인.
- Windows OpenSSH는 SDK 비동기 파이프에서 연결 종료. Git SSH로 동일 검증 통과.
- 중앙 증거: `~/.local/state/waterbe-mcp/install-20261021T023543Z/installation.json`,
  `verified-central-20261021.json`, `verified-windows-20261021.json`.
- 공통 중앙 operations.db에 동일 사건 ID 저장 확인. 수파 게시 완료는 별도 확인 대상.

## 범위와 남은 확인

조회용5개 기존 API만 MCP 실행 가능. native/planned 기능은 발견·설명만 제공하며
저울 쓰기·업로드·매출 동기화 실행은 아직 MCP에 연결하지 않았다.
중앙 워커 재시작·모델 호출·업무 데이터 변경 없이 설치했다.
씽크패드에는 Supabase CLI가 없어 `system.check`의 CLI 점검은 미확인/부분 상태로
반환될 수 있다. REST 이력 조회 성공과 전체 시스템 정상 판정은 다르다.
기존에 열린 Codex 대화의 도구 갱신은 별도이며, 이번 검증은 설정 등록과 실제 SDK
접속 성공까지다. 새 대화에서 `워터비 MCP로 업무 지침부터 확인해줘`로 시작한다.

연결 기준은 [MCP 지침](../guides/WATERBE_MCP_GUIDE.md), Codex 등록 방식은
[공식 MCP 문서](https://developers.openai.com/codex/mcp)를 따른다.
