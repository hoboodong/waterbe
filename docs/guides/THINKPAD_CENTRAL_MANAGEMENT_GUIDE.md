# 씽크패드 코덱스 중앙 관리

## 담당과 실행 장소

중앙 프로그램의 운영 담당은 씽크패드의 워터비 Codex CLI다. 사용자 창구는 기존
Telegram–Waterbe 대화이며 작업 경로는 `/home/sdg/waterbe`다. 새 세션도 이 문서와
AGENTS/WATERBE_GUIDE를 읽고 현재 원본으로 판단한다. Windows는 원격 개발/접속
호스트일 뿐 중앙 워커를 다시 켜지 않는다. 시코드 UI/앱 구현과 카스씨엘 저울 통신의
소유권은 바뀌지 않는다. 각 프로젝트 변경 전 해당 AGENTS와 담당 지침을 읽는다.

## 요청을 받으면

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
