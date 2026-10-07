# 씽크패드 공통 접속

## 현재 중앙 운영 입구

중앙 점검·복구 담당 Codex는 [중앙 관리 지침](THINKPAD_CENTRAL_MANAGEMENT_GUIDE.md)을
읽는다. `~/.local/bin/waterbe-central manage check`가 공통 관리 입구다.

모든 활성 중앙 워커의 실행 주체는 씽크패드다. Windows 예약 작업을 다시 켜지 않는다.
이는 상시 통신·자동 수집의 기준이며 요청형 매출 동기화·OCR·검산까지
씽크패드 전용으로 제한하지 않는다. [운영 실행 기준](OPERATING_EXECUTION_GUIDE.md)을 따른다.
Linux에서 `~/.local/bin/waterbe-central status` 또는
`~/.local/bin/waterbe-central api call history.status`로 확인한다.
Windows에서는 `ssh thinkpad '~/.local/bin/waterbe-central status'`를 사용한다.
이 입구가 중앙 전용 인증과 venv를 명시 로드하며 비밀을 출력하지 않는다.

`namseon-check`는 Drive dry-run, `namseon-sync`는 승인된 동기화 때만 사용한다.
후자는 기존 원본 정리/중복 휴지통/클라우드 적재/DB 업로드를 포함한다.
`daeyoung-ocr <기존 인자>`는 명시적 mobile det/CPU1thread,
`daeyoung-publish <기존 인자>`는 승인된 적재다. 상태 조회로 실행하지 않는다.
`backup`은 인증 제외 운영 상태 온라인 백업이며 자동 스케줄도 설치했다.
정전의 외부 감시/다른 컴퓨터 자동 복원은 이 운영 이전과 별도 과제다.

설치 코드·상태·실제 성공·보류 범위는
[중앙 이전 기록](../plans/THINKPAD_CENTRAL_MIGRATION.md)의 현재 실행 주체 항목을 따른다.

2026-10-05: Windows 중앙 PC에서 `ssh thinkpad` 키 인증 및 재접속 검증.
호스트는 Tailscale `100.123.147.103`, 사용자 `sdg`다. 전용 키는
Windows 사용자 SSH 설정에 있으며 키 내용이나 비밀번호를 Git에 저장하지 않는다.
다른 컴퓨터는 별도 인증 설정이 필요하다.

## 공통 입구

```powershell
./scripts/thinkpad.ps1 status
./scripts/thinkpad.ps1 run -Command 'git status --short'
./scripts/thinkpad.ps1 run -Project cascl5200 -Command 'git status --short'
./scripts/thinkpad.ps1 shell
./scripts/thinkpad.ps1 upload -LocalPath ./example.txt -RemotePath /home/sdg/example.txt
./scripts/thinkpad.ps1 download -RemotePath /home/sdg/example.txt -LocalPath ./received.txt
```

run은 명시된 명령을 원격 프로젝트에서 실행하며 변경 명령도 가능하므로 사용자
요청 범위를 지킨다. 파일 전송은 단일 파일만, 기존 대상이 있으면 중단한다.
업로드의 존재 확인과 전송은 원자적이지 않으므로 동시에 다른 프로그램이 생성하는
경로에는 사용하지 않는다. DB 이전은 이 도구로 실행 중 파일을 복사하지 말고
각 담당 프로그램의 온라인 백업/중단/검증 절차를 따른다.

두 컴퓨터는 별도 파일 시스템이다. 파일 양방향 복제, 서비스 이중 실행,
자동 커밋/push, 자격증명 복제는 하지 않는다. 명령 실패 시 쓰기를 자동 재시도하지
않는다. 접속 설정은 연결 준비이며 중앙 워커 이전 완료를 뜻하지 않는다.
SSH 서버 부팅 자동 활성화 및 SSH/Tailscale 현재 활성 상태는 확인했다.
전원 종료/절전/인터넷 장애까지 해결됐다는 뜻은 아니다.

Codex CLI는 로그인 쉘의 설치 경로를 별도 확인한다. 비로그인 SSH에서
`command -v codex`가 나오지 않았으므로 설치 없음으로 단정하지 않는다.

실측 실행 경로: `/home/sdg/.npm-global/bin/codex`; `--version` 실행 성공
(`codex-cli 0.157.1`). 기본 SSH PATH에는 없으므로 자동화에서는 절대 경로를 쓴다.
버전 확인은 Telegram 연동/인증/자동 관리 정상 검증이 아니다.

## 모든 프로젝트/세션에서 발견

Windows의 워터비·시코드·카스씨엘 AGENTS에서 이 문서를 연결한다.
씽크패드에서도 세 프로젝트 AGENTS가 `/home/sdg/waterbe/docs/guides/THINKPAD_CONNECTION_GUIDE.md`를
읽도록 연결한다. 씽크패드 자체에서는 SSH로 자신에게 접속하지 않고 Linux 명령을
직접 실행한다. Windows 전용 `thinkpad.ps1`을 Linux에서 실행하지 않는다.
세션이 이전 지침을 이미 읽었다면 변경된 AGENTS와 이 문서를 다시 읽는다.
공통 계약을 쓰되 모든 컴퓨터에 동일한 파일/권한이 있다고 가정하지 않는다.

## 코드 최신 유지 — 사용자 승인 2026-10-05

GitHub origin/main을 공통 기준으로 삼는다. Windows의 Waterbe Repository Sync
예약 작업과 씽크패드 waterbe-repo-sync.timer가 분당 확인하며, main이 뒤처지고
tracked 작업본이 깨끗할 때만 fast-forward한다. 미커밋 작업, 앞선 로컬 커밋,
분기 충돌, 파일 충돌을 덮거나 stash/reset하지 않고 상태를 남겨 Telegram에 알린다.
같은 HEAD의 개발 중 작업본은 정상 보존한다. 커밋·푸시는 작업 에이전트가 요청에
따라 수행한다. 미커밋 파일을 실시간 복제하는 시스템이 아니다.

상태는 Windows LOCALAPPDATA/Waterbe/repo-sync.json, 씽크패드
~/.local/state/waterbe-central/{repo-sync,windows-repo-sync}.json에 보존한다.
연속 실패2회/회복은 기존 공통 이력·Telegram 경로를 쓴다. source는
central_repo_sync/central_windows_sync다. Windows 전원 종료/SSH 자체 불통의
외부 감시는 별도이며 상태 파일의 checked_at이 오래되면 현재 정상으로 보지 않는다.

소스 갱신은 앱 배포나 불변 워커 릴리스 교체/서비스 재시작이 아니다. canonical 소스를
직접 사용하는 요청형/oneshot 도구는 다음 실행에 갱신된 코드를 사용할 수 있다.
실행 코드의 변경은 각 담당 적용·검증 절차와 실행 릴리스를 확인한다.

20:11 KST 양쪽 main을 f398aca로 일치시킨 뒤 자동 최신 확인 설치/실행 통과.
Windows 작업은 현재 사용자 Interactive이므로 로그아웃/PC 종료 때 실행하지 않는다.
씽크패드 사용자 timer는 Linger로 독립 실행한다. 이전 미커밋 이전 작업본은
씽크패드 `migration-working-copies-before-published-sync-20261005` stash에 보존했다.
DB/인증은 Git 동기화 대상이 아니며 코드 상태는 실행 릴리스 상태와 구별한다.
