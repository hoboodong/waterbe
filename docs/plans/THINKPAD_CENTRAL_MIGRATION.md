# 중앙 Windows → 씽크패드 전환

## 2026-10-05 부분 전환 실적

### 추가 전환 (18:49 KST 전후)

- 씽크패드 SSH 매장 별칭 등록. 월계도 공개키 인증을 보완해 접속 확인.
  왕십리만 현재 Tailscale offline/SSH timeout; 이 상태를 정상으로 바꾸지 않는다.
- 중앙 읽기: 처리 중 요청 0건 확인 후 Windows `CASPi Remote Read Worker` 중지/
  비활성화, 씽크패드 `caspi-remote-read.service` enable/active/idle 확인.
  클라우드 요청과 원래 operation_id/lease 계약 유지. 실제 폰 신규 요청 검증은 별도.
- 영수증: Windows `CASPi Receipt Sync` idle에서 비활성화, cursor SQLite 온라인 백업/
  integrity 검증 후 이동. `caspi-receipt-sync.timer` 분당 실행, 실제 3건 publish ACK
  확인. 기존 범위인 문어팀만 유지하며 다른 매장 전체 게시로 확대하지 않는다.
- 누계: Windows `CAS CL5200 Aggregate Central Sync` idle에서 비활성화,
  중앙 SQLite 온라인 백업 후 씽크패드 `cas-aggregate-sync.timer` 분당 실행.
  최초 실제 import 2회차, 왕십리만 `partial/ssh_export_failed`; 다른 매장 진행.
- 현재 누계 원본 중앙 DB는
  `/home/sdg/.local/state/cas-central/aggregate-central.sqlite3`.
  Windows 기존 DB는 원복용 정지본으로 최신 운영 조회에 쓰지 않는다.
- `central_aggregate_runner.py`는 CAS 기존 importer를 사용하고 출처별 실패2회/
  실제 읽기 재개를 공통 history 건강 사건과 임시 알림 bridge로 연결한다.
  수집 성공은 물리 저울 실시간 읽기/생산금액 확정과 다르다.
- 중앙 읽기8/영수증6/누계5 단위 테스트 통과. 서비스/설정 검증 통과.
  Windows 상품/문구 변경·새로고침 통합 워커와 Telegram reporter는 아직 유지.
  변경 워커의 verified target index/백업/작업 상태 및 Windows reserve 실행 경로를
  검증한 뒤 전환한다. 기존 GPT 보고를 Codex CLI로 넘기는 단계도 아직 미완료.

- 사용자 승인으로 기존 중앙 Supabase 인증을 씽크패드 제한 설정 파일에 전달.
  `~/.config/waterbe/central.env` 권한 600, 상위 폴더 700. 실제 read-only 조회 통과.
- 공통 기록 워커 `waterbe-history.service` 활성/부팅 자동 실행. Linger=yes.
  Windows `WaterbeOperationHistory`는 Disabled. 다른 중앙 워커는 Windows 유지.
- 온라인 백업 95,309 사건/전송 대기 0/격리 0/integrity_check 통과.
  원본 백업과 원격 DB SHA256
  `25bb222a7f5b314d10b775b1f9bad1c9844059b814cc45d89cb63d4943a51376` 일치.
- 실제 수집에서 22개 출처 available, 새 기록 및 cloud ACK 확인. 소스 조회 성공은
  물리 저울의 현재 성공과 다르다. master YAML은 의미 내용 일치 확인했으나 CRLF/LF가
  달라 파일 해시 9건의 새 버전 관측이 생겼다. 업무 내용 수정 사건으로 해석하지 않는다.
- 알림 전달은 임시 Windows `WaterbeThinkpadHistoryBridge`(분당1회)가 원격 건강
  로그를 기존 reporter 로그 폴더로 전달한다. 기존 GPT/Telegram reporter 미이전.
  새 씽크패드 notices 디렉터리는 기존 미해결 Telegram 메시지를 복제/재전송하지 않는다.
- 씽크패드 기존 공개키를 마포/미아/문어 authorized_keys에 추가, Windows에서
  이미 신뢰한 호스트키 등록 후 실제 접속 확인. 월계/왕십리는 SSH 시간 초과로 보류.
  기존 키 삭제/교체, 저울값/네트워크 설정 변경 없음.
- 이력 관련 14 tests 통과. 전원 장애 외부 감시/Windows 자동 예비 전환 미구현.
  최초 부분 전환 이후 추가 실적은 위 항목을 따른다. 상품 쓰기/매출 수집/
  Telegram 코덱스 관리는 이전 완료로 표시하지 않는다.

## 2026-10-05 전환 전 확인 (현재 상태는 위 실적 참조)

- 목표 호스트: `sdg@100.123.147.103`; 전용 SSH 키 접속 검증.
- SSH/Tailscale 활성, 사용자 `Linger=yes` 확인. 기존 Telegram terminal-bot-waterbe
  및 세션 watchdog 실행 중. 이 서비스는 이전 작업에서 중지하지 않는다.
- 로그인 환경의 SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY 미설정.
  다른 프로젝트 .env를 탐색/복사하거나 Windows 키를 임의 복제하지 않는다.
- Windows 누계 수집/상품 변경/중앙 읽기/영수증 게시/Telegram reporter/공통 이력
  워커는 아직 기존 실행 주체다. 이 문서는 전환 완료 증거가 아니다.

## 전환 순서

1. 각 워커의 코드 버전/의존성/설정/원본 DB/큐/처리 위치/로그/인증을 목록화한다.
   Windows 전용 DPAPI, winreg, PowerShell 및 경로는 Linux 호환 경계로 바꾼다.
2. 사용자 승인으로 중앙 전용 인증을 씽크패드의 권한 제한 파일에 설정한다.
   키는 Git/대화/로그에 남기지 않는다. Telegram 기존 연결은 계약을 확인한 후 사용한다.
3. 실행하지 않는 상태에서 Linux 코드와 systemd 서비스, 재시작/상태 조회를 준비한다.
4. 워커별 Windows 예약 실행을 중지하고 진행 작업이 안전하게 끝난 것을 확인한다.
   쓰기 미확정은 보존/재확인하며 중간에 강제 종료해 새 요청으로 재쓰기하지 않는다.
5. SQLite 온라인 백업으로 데이터/처리 위치/전송 대기를 옮긴다. 파일 해시와
   integrity_check, 행수 및 큐/격리 상태를 비교한다. 실행 중 DB 단순 복사 금지.
6. 씽크패드 단독 실행 후 실제 수신/ACK/중복 억제/상태/알림을 확인한다.
   서비스 active만으로 업무 성공을 주장하지 않는다. 앱 APK 배포는 하지 않는다.

## 장애 및 원복

- 워커 프로세스 실패는 systemd 제한 재시작과 별도 알림으로 처리한다.
- 네트워크 실패는 큐/처리 위치 보존 후 동일 ID 재개. 불명확한 저울 쓰기 재전송 금지.
- Windows는 예비로 보존하되 자동 동시 활성화하지 않는다. 원복 전에 씽크패드
  실행 중지/미확정 작업/새 데이터 및 큐를 확인하고 최신 상태를 예비로 반영한다.
- 씽크패드 전원/호스트 장애는 다른 호스트의 생존신호 감시가 필요하다. 아직 미설치.
- 코덱스 관리 담당 연결/권한/알림 계약은 별도 검증 전이며 기존 GPT reporter를
  검증 없이 끄지 않는다. Linux 공통 이력 notices의 Telegram 소비자도 연결 전이다.

## 준비한 서비스

`scripts/waterbe-history.service`는 공통 이력 설치 기준 파일이며 위 실적대로 활성화했다.
인증 파일은 `~/.config/waterbe/central.env`, 코드 릴리스는
`~/.local/lib/waterbe-history`, 상태는 `~/.local/state/waterbe-history`다.
실제 전환 때 고정 릴리스/온라인 백업/인증 권한/단독 실행 및 알림을 검증한다.
