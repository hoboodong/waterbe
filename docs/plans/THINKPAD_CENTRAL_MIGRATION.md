# 중앙 Windows → 씽크패드 전환

최종 완료 조건은 [중앙 컴퓨터 교체·재해 복구 계약](CENTRAL_DISASTER_RECOVERY.md)을
포함한다. Windows 고장 시 원본 PC 접근 없이 코드·인증·데이터·미확정 작업을
복원할 수 있어야 하며, 단순 호스트 이동을 전체 완료로 표시하지 않는다.

## 2026-10-05 부분 전환 실적

### 현재 실행 주체 — 19:30 KST 전후 전환 확인

- 운영 이력, 중앙 읽기, 문어팀 영수증 게시, 누계 가져오기, 상품·문구 변경,
  Telegram 보고는 모두 씽크패드 단독 실행이다. 해당 Windows 예약 작업과
  임시 `WaterbeThinkpadHistoryBridge`는 Disabled. 과거 실패 감지/triage 작업은
  이미 비활성인 구 시스템이므로 다시 활성화하지 않았다.
- 변경 서비스: `cas-supervisor.service`, 코드
  `~/.local/lib/cas-supervisor-20261005`, 상태 `~/.local/state/cas-supervisor`.
  실제 Windows 원본 백업 루트는 `D:/CAS-CL5200/snapshots`였다. 기본 AppData
  준비본과 구별하여 이 실제 루트의 모든 백업·assistance state·검토된 circuit
  증거를 최종 전송했다. 네 변경 대상의 최신 PLU 인덱스 전건 검증 통과
  (마포81/미아76/왕십리76/월계76). 문어팀의 기존 쓰기 비활성은 유지한다.
- 네 처리 큐의 processing=0 확인 후 Windows 워커 중지. 상품/문구 dispatch DB
  온라인 백업 integrity/전송 해시 검증, 기존 ID·동일 요청 해시 보존. 운영 JSON
  증거도 별도 이전했다. 임의 쓰기·재전송·원본 성공 처리 없음.
- Linux 사용자 영역 PowerShell 7.6.6 및 `powershell.exe`/`python.exe` 호환 경로.
  venv `~/.local/opt/waterbe-central-venv`에 Windows와 같은 realtime2.31.0 설치.
  실제 Realtime subscribed 및 마포 자동 검증 81records/verified/changed=false 확인.
  검증된 최신값은 앱 스냅샷 게시 기준이며 물리 쓰기 시험은 하지 않았다.
- 왕십리 Windows 접속이 재개되어 씽크패드의 기존 공개키를 추가했다. 기존 키는
  삭제하지 않았다. 다섯 매장 SSH/CASPi status ready 확인. 이후 실제 중앙 누계
  import succeeded/새6회차/매장 오류 없음. 이는 물리 저울 전부 정상의 증거는 아니다.
- `cas-telegram-reporter.timer` 30초 간격 실행. 같은 봇/수신처/전송함/known IDs
  유지. Windows DPAPI 인증을 Linux 제한 파일 `~/.config/waterbe/telegram.env`
  (600)로 전송. 실제 Telegram canary accepted 증거는 reporter 상태 폴더의
  `thinkpad-migration-test.json`. 기존 delivery_uncertain1건은 그대로 보존하고
  재전송하거나 성공 처리하지 않았다. 임시 Windows 로그 bridge는 중지했다.
- 남선 원본 접근/449파일 탐색 dry-run 성공. Windows 장부9048행(8/28~9/29)은
  보존본으로 이전. 기존 씽크패드 장부127515행(2025/7/5~2026/10/2)을 유지했다.
  같은 source ID는 모두 존재하지만 2829행의 내용 차이는 미조정이며 두 장부를
  임의 합치거나 덮지 않았다. 공용 매출 기준은 기존 Supabase다. 매출 요청형
  실행은 `waterbe-central namseon-sync`; 신규 상시 매출 스케줄을 만들지 않았다.
- 대영 PaddleOCR3.7.0/Paddle3.3.1 및 기존 모델 캐시 이전. server det 시험이
  종료137로 실패하여 중앙 실행은 명시적 mobile det/CPU1thread 사용. 샘플 실제
  predict 30텍스트 통과. 원본 OCR 기본 모델은 보존하고 `--det-model` 옵션만 추가.
  매출 판독 정확성/합계 검토는 기존 지침을 따르며 신규 매출 적재는 하지 않았다.
- 기존 ThinkPad `terminal-bot-waterbe`/session watchdog 및 실행 중 Codex 유지.
  CLI ChatGPT 로그인 상태 확인. 운영 창구는 기존 Telegram 대화이며 새 자동
  AI 진단/수리 에이전트를 추가한 것은 아니다. 일반 알림은 AI 없이 동작한다.
- `waterbe-central-health.timer`가 중앙7종 실행/타이머 상태를 관측하고 기존
  공통 사건/내구성 notice/Telegram 경로로 연속 실패2회 및 재개를 연결한다.
  프로세스 회복을 저울 적용 성공으로 보고하지 않는다. 호스트 자체 정전의 외부
  감시는 별도이며 이 동일 호스트 관측기가 정전을 알린다고 주장하지 않는다.
- `waterbe-central-backup.timer`: 매일00/06/12/18:30, 온라인 SQLite6종 integrity
  확인 후 완료 폴더 공개. 최초199파일 백업 성공. 실제 D루트 최종 백업과 추가
  운영 JSON 반영 후19:34 KST 백업 `20261005T103446.073259Z`의729파일/SQLite6종을
  독립 해시·DB 검사로 재검증했다. 이전 준비 백업은 임시 WAL/SHM 파일 문제로
  복원 검증 합격본으로 사용하지 않는다. SQLite 연결을 닫은 뒤 manifest를 만드는
  수정과 회귀 테스트를 적용했다. 독립 검사는 `central_backup_verify.py`로 워커를
  시작하지 않고 실행한다. 이 백업은 인증을 포함하지 않으며 별도
  컴퓨터 복원 시험/외부 암호화 비밀 보관까지 완료됐다는 뜻은 아니다.
- 프로젝트 소스는 fast-forward로 Waterbe906ec90/CAS55ab424/SeaCode2896db5 반영.
  이전 씽크패드의 지침 추가만 `thinkpad-pre-migration-20261005` stash에 보존했다.
  이번 추가 스크립트/설치 문서는 작업본을 명시 전송하며 코드 푸시/APK 배포와
  구별한다. 다른 세션의 미커밋 작업은 건드리지 않았다.

- 테스트: reporter27/bootstrap3/supervisor25/remote adapter6 통과. Linux에서도
  reporter27/bootstrap3 재실행 통과. 샘플 OCR30텍스트/Drive read+dry-run/
  cloud history gateway available 확인. 신규 실제 저울 쓰기 시험은 하지 않았다.

아래 부분 전환 항목은 이전 단계의 이력이다. 현재 실행 주체는 이 항목을 따른다.

### 추가 전환 (18:49 KST 전후)

- 푸시 기준: Waterbe `906ec90`, CAS `55ab424`, SeaCode `2896db5`.
  이후 다음 작업으로 bootstrap의 Linux 명시 환경 지원 준비/3 tests 통과.
  통합 워커 전체 상품 새로고침/백업은 `powershell.exe` 기반 controller 경로여서
  Linux 실행 및 CASPi 경로 계약 검증이 남는다. Windows 통합 워커를 중지하지 않는다.

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
