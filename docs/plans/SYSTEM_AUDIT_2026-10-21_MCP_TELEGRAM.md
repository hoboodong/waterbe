# 기존 Telegram 워터비 세션 연결·전체 점검

확인: 2026-10-21 12:17~13:03 KST. 공통 사건 `waterbe-system-audit-20261021-1301`.
코드 기준 `4cf8e5b41b348cbd730eaad989f2032743476d74`.
판정: **MCP/기존 세션 연결 확인, 운영 전체는 일부 문제 있음(partial)**.

## 기존 세션 연결 기록

- 대상은 씽크패드 tmux `waterbe`의 기존 Telegram/Codex 대화다.
  새 대화 생성·모델 교체·기존 세션/Telegram 중단 없이 유지했다.
- 전역 Codex 워터비 한정 시작 안내와 `waterbe-codex` 실행 입구를 설치했다.
  백업: `~/.local/state/waterbe-mcp/codex-startup-20261021T031341Z`,
  CLI 연결 보완 설치: `codex-startup-20261021T031728Z`.
- 해당 대화에서 직접 새 MCP 도구를 호출하지 못함을 확인했다. `/mcp` 목록의
  `waterbe: unknown (10 tools)` 표시만으로 실제 모델 호출 성공을 주장하지 않았다.
- 기존 셸 기능에서 `~/.local/bin/waterbe-mcp-call`로 **같은 MCP**를 호출하도록 했다.
  별도 업무 로직/새 AI/새 저울 writer가 아니다. 지침·입력·작업 ID·결과가 같다.
- 사용자 승인 범위에서 기존 대화에 읽기 검증을 전달했고, 해당 세션이
  waterbe_start/history.status 연결·조회 성공을 보고했다. 현재 점검에서도
  동일 CLI exit0/history.status available/상태1행을 독립 재확인했다.
- 관련 source: 9ed80ea(시작 안내), 4cf8e5b(기존 세션 MCP CLI).
  입력/재실행/실패 기준은 [MCP 지침](../guides/WATERBE_MCP_GUIDE.md)을 따른다.

## 정상 확인 범위

| 항목 | 확인 결과 |
| --- | --- |
| Git | Windows/씽크패드 Waterbe HEAD=origin/main=4cf8e5b, fetch 성공 |
| 회귀 | Windows36개·씽크패드36개 통과 |
| MCP | Windows→SSH 및 중앙 현지 연결, 도구10개·리소스·프롬프트·이력 조회 성공 |
| 수파 | Windows 기존 CLI 직접 조회: ACTIVE_HEALTHY, 연결26, 대기 잠금0, DB482,692,243bytes |
| 오래된 활성 연결 | 약21시간 연결은 walsender/Client/WalSenderWaitForWal. 업무 쿼리 정체로 단정하지 않음 |
| 공통 이력 | 연결된22개 출처 available/recent(점검 정책20분 이내), delivery대기0·격리0 |
| CASPi | 마포·미아·월계·왕십리 active, 최초 점검 최근 누계 관측33~105초 |
| 핵심 중앙 | history/read/supervisor 실행 중, reporter/backup/repo-sync 최근 종료0 |

`system.check`의 checked_at=2026-10-21T04:01:30.688177+00:00.
자료 조회 성공·서비스 active와 실제 업무 정상은 구별한다. DB의 장기 활성 연결은
backend_type/wait_event 메타데이터만 추가 조회했으며 세션을 종료하지 않았다.

## 발견된 문제와 이후 확인

1. **문어팀 장비 미접속**: mooner2 SSH 실패. 중앙 누계 importer의
   `ssh_export_failed:mooner2`, receipt sync의 `caspi_receipt_fetch_failed:mooner2`가
   남아 partial/종료1을 유발한다. 다른 매장 처리는 계속된다.
2. **월계 누계 일시 실패**: 직전 importer 기록에 scale_collection_failed가 있었고,
   다음 기록에는 월계 오류가 사라지고 새 collection1건 적재됐다.
   장비 최근 로그에서도 aggregate_schedule_completed/succeeded 확인.
   이것은 해당 회차 후 성공이며 반복 장애 전체 해소를 뜻하지 않는다.
3. **마포·월계 변경 감지 오류**: 최근15분/최대120개 journal 범위에서
   read_feed_failed/ValueError가 마포4건·월계52건 관측됐다.
   미아·왕십리 같은 범위에서는 관측되지 않았다. 전체 기간의 오류 총계가 아니다.
   해당 기간 누계 성공도 함께 존재한다. 변경 피드 실패를 누계 중단과 혼동하지 않는다.
   어느 PLU/문구와 어떤 검증 단계인지 로그만으로 확정하지 못했으며 원인 조사 필요.
4. **중앙 상태 감시의 실패 표시**: aggregate/receipts의 partial/종료1 또는
   실행 중 상태가 health 판정에 반영된다. 실행 중은 미확정(null)으로 구별한다.
   감시 서비스 하나의 실패 표시만으로 모든 워커가 멈췄다고 판단하지 않았다.

조치 후보: 변경 피드의 실패 대상/실제 읽기 영수증 대조 → 대상별 원인 확인과
수정 승인 → 동일 대상 새 성공/앱 게시 검증. 실패 로그 삭제·전 매장 재시작·
미확정 쓰기 재전송·문어팀을 성공으로 숨기는 처리는 하지 않았다.

## 보존·한계

- 다른 세션의 미커밋 코드/품질/운영 기록은 이번 커밋에 섞거나 덮지 않는다.
- 점검은 읽기 전용이다. 기록 추가 외 저울 쓰기·매출 동기화·재시작·DB 변경 없음.
- 휴대폰 실제 화면/Bluetooth·인쇄·실제 신규 저울 쓰기·수파 I/O 예산/CPU/RAM은
  이번 확인으로 정상 판정하지 않는다. 매출 출처 조회 성공은 당일 매출 완결 증명이 아니다.
- MCP 검증 증거: 중앙 `~/.local/state/waterbe-mcp/verified-system-audit-20261021.json`.
  최초 출력/원시 journal/DB는 Git에 넣지 않고 시각·분류·근거 경로만 이 기록에 남긴다.
