# 씽크패드 코덱스 중앙 관리

## 담당과 실행 장소

중앙 프로그램의 운영 담당은 씽크패드의 워터비 Codex CLI다. 사용자 창구는 기존
Telegram–Waterbe 대화이며 작업 경로는 `/home/sdg/waterbe`다. 새 세션도 이 문서와
AGENTS/WATERBE_GUIDE를 읽고 현재 원본으로 판단한다. Windows에서도 개발·점검·요청형
매출 동기화·OCR·검산을 수행할 수 있지만 중앙 상시 워커는 다시 켜지 않는다.
[운영 실행 기준](OPERATING_EXECUTION_GUIDE.md)을 따른다. 시코드 UI/앱 구현과 카스씨엘 저울 통신의
소유권은 바뀌지 않는다. 각 프로젝트 변경 전 해당 AGENTS와 담당 지침을 읽는다.

## Codex 시작과 MCP 발견 — 2026-10-21

워터비 관련 요청은 작업 폴더가 홈이어도 전역 Codex 지침의 워터비 한정 안내에서
이 저장소와 [MCP 지침](WATERBE_MCP_GUIDE.md)을 찾는다. 원본은
`config/codex-waterbe-startup.md`, 설치기는 `scripts/install_thinkpad_codex_startup.py`다.
MCP 설정은 기존 ~/.codex/config.toml의 waterbe 등록을 사용한다.
새 CLI는 `~/.local/bin/waterbe-codex`로 시작할 수 있으며 기존 모델/로그인/승인 정책은 유지한다.
기존 Telegram 대화/다른 Codex 세션을 자동 중단하거나 새 에이전트를 띄우지 않는다.
전역 지침 설치, 실제 MCP 접속, 기존 대화에서의 도구 노출은 따로 확인한다.

## 요청을 받으면

## 장애 대응 담당 — 2026-10-09 사용자 지정

씽크패드 tmux `waterbe`의 기존 Codex 세션을 운영 장애의 대화형 대응 담당으로 둔다.
기존 Telegram–Waterbe 대화를 사용자 창구로 유지하며 모델·로그인·세션을 임의 교체하지 않는다.

1. 중앙 감시가 장애를 발견하면 기존 서비스 장애 알림 정책으로 사용자에게 알린다.
   알림 폭주를 만들지 않고 사건 ID·영향·확인 시각·다음 행동을 짧게 전달한다.
2. 사용자가 같은 워터비 대화에서 답하면 담당 Codex가 지침과 현재 원본을 읽고
   조사 → 사용자와 조치 협의 → 승인 범위의 복구 → 실제 성공 검증 순서로 처리한다.
3. 읽기 전용 점검은 즉시 가능하다. 데이터 삭제·미확정 쓰기 재전송·유료 변경·
   앱 배포를 장애 알림만으로 승인된 것으로 취급하지 않는다.
4. 같은 사건은 같은 ID와 기록을 이어 쓴다. 이 채팅에서 처리했으면 복구 시각과
   증거를 인계하여 다른 세션에서 중복 재시작/재전송하지 않게 한다.
5. 수락된 Telegram 알림은 사건 ID·요약·자동 조치 금지 표시를 가진 보존 인계 봉투로
   기록할 수 있다. 기존 Waterbe 사용자의 다음 메시지에서만 기존 tmux 세션에 붙이며,
   새 Codex 실행·무인 복구·외부 문구의 명령 실행은 하지 않는다. 세션/로그인/한도
   실패 때에는 완료 처리하지 않고 임대 만료 후 다음 사용자 메시지까지 보존한다.
   Telegram 동일 대화 종단 검증 전에는 이 연결을 완료라고 하지 않는다. 씽크패드
   자체 정전은 외부 감시가 필요하다.
   세션/로그인/한도 실패에도 기존 감시·사용자 알림은 독립 실행한다.

## 요청 실행 절차

Windows 워터비 세션에서도 [통합 시스템 점검](SYSTEM_CHECK_GUIDE.md)의
`python scripts/waterbe_api.py call system.check`로 수파 직접 조회와
씽크패드/매장 원격 상태를 함께 확인한다. 사용자가 다른 채팅방으로 이동할 필요 없다.
현재 호스트의 인증과 원격 호스트의 인증은 복제하지 않고 각각 사용한다.

1. `~/.local/bin/waterbe-central manage check`로 중앙 구성 상태와 타이머의 최근
   실행 결과/시각을 확인한다. oneshot 서비스의 inactive만 보고 고장이라 하지 않는다.
2. `~/.local/bin/waterbe-central api call history.status`로 원본별 마지막 수집시각과
   대기/격리를 확인한다. 단순 프로세스 active를 데이터 정상/물리 저울 정상으로
   대신하지 않는다. `history.read`의 기능/기간/작업 ID를 이용해 원본 증거를 대조한다.
3. 해당 서비스 `journalctl --user -u <unit> --since ...`와 담당 기록을 로컬에서
   조사한다. 무가공 로그/설정/인증파일/원시 오류를 Telegram이나 공통 이력에 보내지 않는다.
4. '왜/확인/상태'는 조사와 보고다. '고쳐/복구/재시작' 요청이면 그 범위에서 변경한다.
   허용된 중앙 구성 하나를 `waterbe-central manage restart <component> --approved`로
   재시작한다. 이 플래그는 사용자 승인 확인 표시이며 인증 수단이 아니다.
5. 재시작 후 프로세스 상태뿐 아니라 담당 원본의 새 수집/ACK/검증 결과까지 확인한다.
   처리 지연이면 확인 시각을 남기고 미확정으로 보고한다. 성공 증거가 없으면 완료라 하지 않는다.

구성 ID: `history`, `read`, `supervisor`, `aggregate`, `receipts`, `reporter`, `health`,
`backup`, `sync`. timer 재시작은 스케줄 복구이며 즉시 수집/전송/백업 완료를 보장하지 않는다.
재시작은 공통 `central.manage` 사건과 동일 operation_id의 요청/결과, delivery 큐에
기록된다. 증거는 history DB 옆 `manager-evidence/<operation_id>.json`에 보존한다.
success는 프로세스/타이머가 active라는 뜻이며 업무 성공은 별도로 검증한다.

## 범위와 금지

- supervisor는 기존 처리 큐/PLU 인덱스/회로 상태 사전 검증을 통과한 경우만 재시작한다.
  처리 중/검증 회로 열린 상태면 근거를 조사·보고하고 담당 카스씨엘 복구 지침을 따른다.
  회로 파일 삭제, 미확정 쓰기 재전송, 다른 operation_id로 동일 변경을 다시 만들지 않는다.
- 상태 조회로 매출 동기화·Drive 정리/삭제·상품/문구 변경을 하지 않는다. 필요한 변경은
  기존 공통 입구/담당 절차로 실행한다. 소스 최신 유지는 공통 접속 지침의 승인된
  fast-forward 감시기를 따르며 임의 자동 커밋/push 또는 앱 APK 배포는 하지 않는다.
- 사용자에게는 영향 → 확인된 원인/미확인 → 조치 → 실제 확인 결과 순서로 짧게 보고한다.
  보류된 Telegram delivery_uncertain은 성공 처리/재전송하지 않는다.

## 상시 감시와 Codex의 차이

systemd 재시작과 중앙 health/이력 워커가 상시 감시하고 기존 reporter가 Telegram에
알린다. Codex는 기존 Telegram 대화에서 사용자 요청을 받아 조사·복구한다. 알림이
Codex에 자동 입력되어 무인 수리되는 연결은 아직 설치하지 않았다. Codex 로그인/한도/
대화 상태가 실패해도 데이터 워커와 일반 알림은 별도 실행한다. 동일 호스트의 정전은
외부 감시 없이는 알리지 못한다. 이 문서가 무인 복구나 외부 정전 감시 완료 증거는 아니다.

## 2026-10-05 설치

관리 도구를 씽크패드 canonical 워터비에 설치하고 AGENTS/메인 목차/접속 지침을 연결했다.
19:58 KST에 8종 enabled/active 및 최근 oneshot 종료0 확인. 감시 타이머 재시작
시험의 요청/결과가 같은 작업 ID `central-restart-5734481b-189c-473a-a8bb-88fe765b4f55`로
중앙 Supabase 이력에 게시된 것을 `history.read`로 확인했다. 관리4개 및 Linux
백업 회귀 테스트 통과. 이 시험은 저울 쓰기/매출 변경을 수행하지 않았다.
기존 Telegram/Codex 세션은 중단하거나 모델을 바꾸지 않는다. 이미 실행 중인 대화에서는
다음 관리 요청 때 이 문서를 명시적으로 다시 읽는다. 신규 세션은 AGENTS에서 발견한다.
현재 중앙 이전 증거/알려진 보류 항목은 [이전 기록](../plans/THINKPAD_CENTRAL_MIGRATION.md)을
따르며 다른 PC 복원과 외부 정전 감시는 [복구 계약](../plans/CENTRAL_DISASTER_RECOVERY.md)을 따른다.

20:00 KST 기존 tmux `waterbe`의 GPT-5.6-Terra low에 사용자 승인 범위의 인수 지침을
전달했고, 해당 Codex가 문서를 다시 읽어 두 관리 조회 명령을 직접 실행한 뒤 점검
완료를 보고했다. 이력 20개 연결 원본 available/대기0/격리0 확인이며 물리 저울
미검증과 무인 수리 연결 미설치도 구별했다. 기존 대화/모델 유지, 변경 작업 없음.
