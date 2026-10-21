<!-- BEGIN WATERBE MCP STARTUP -->
## 워터비 관련 업무의 공통 시작

이 절은 워터비·시코드·CASPi·카스씨엘·매장 저울·워터비 매출 업무에만 적용한다.
다른 프로젝트의 업무 범위를 확대하거나 사용자 요청 없이 워터비 작업을 시작하지 않는다.

- 작업 폴더가 홈/다른 경로여도 `/home/sdg/waterbe/AGENTS.md`와
  `/home/sdg/waterbe/WATERBE_GUIDE.md`에서 담당 지침을 찾는다.
  세션 시작·재개 시 지침의 최신 커밋 확인을 먼저 하고 미커밋 변경은 보존한다.
- `waterbe` MCP가 연결돼 있다. `waterbe_start` → 지침 검색·끝까지 읽기 →
  기능 목록·입력 계약 확인 → 실제 사용자 요청 범위의 실행 → 원 작업 결과 검증 순서다.
  구체적인 도구명·계약은 `/home/sdg/waterbe/docs/guides/WATERBE_MCP_GUIDE.md`를 읽는다.
- 기본 조회는 `waterbe_call`. 확장 기능은 `waterbe_prepare_action` 및
  `waterbe_submit_action`, 결과 확인은 `waterbe_action_status`를 사용한다.
  같은 작업 UUID는 재접속 뒤에도 유지한다. 접수/finished를 실제 저울 적용으로 보고하지 않는다.
- 기존 기능을 MCP가 금지하는 것은 아니다. 미구현 공통 API는 해당 업무 지침의 기존
  수동·CLI 절차를 따른다. MCP 장애는 실제 기록 없음·매출0·저울 미실행의 증거가 아니다.
- 도구가 안 보이면 설정과 현재 세션의 도구 노출을 구별한다.
  기존 대화를 교체하지 않고 `~/.local/bin/waterbe-mcp-call waterbe_start`로 같은
  MCP를 호출할 수 있다. 예: `waterbe-mcp-call waterbe_call --arguments
  '{"operation":"history.status"}'`. 복잡한 인자는 `--arguments -`의 stdin JSON을 쓴다.
  이 입구는 동일 MCP를 호출하는 클라이언트이며 별도 저울 실행기/새 AI가 아니다.
  `/home/sdg/.npm-global/bin/codex mcp get waterbe`로 등록을 확인할 수 있다.
  필요하면 사용자에게 기존 대화의 연결 갱신/재개를 안내한다. 다른 세션/Telegram bridge를
  임의 종료·재시작하거나 새 AI 세션을 띄워 대신 작업시키지 않는다.
- 상시 워커는 씽크패드에서 유지한다. 사용자 요청 없이 저울 쓰기/동기화/재시작/
  알림 발송을 시험하지 않는다. 앱 배포·개인별 권한은 기존 지침 그대로다.
- 비밀은 기존 중앙 환경에 두며 Windows·채팅·Git으로 복사하지 않는다.

새 워터비 CLI 대화는 `~/.local/bin/waterbe-codex`로 시작할 수 있다.
모델·로그인·승인 정책을 이 안내에서 변경하지 않는다.
<!-- END WATERBE MCP STARTUP -->
