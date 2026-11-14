# 월계 연결 소유자 적용

사용자 승인: 다른 매장 비교와 해결 방법 설명 후 `ㅇㅇ`.
작업 범위는 월계 연결 경로 정리와 중앙 전체조회 전환이다.
다른 매장 배포·앱 APK 배포·물리 상품/문구 쓰기는 하지 않았다.

## 기준과 설치 상태

- Waterbe fetch 성공, HEAD/origin
  `6f2eebdaf3f7c7f57115a213da8c3a23665ccb37` 확인. 기존 dirty 자료 보존.
- CAS 원본 HEAD `6f5de6bb45dce18ece40d2511c9d627fcf3cd0c4`, origin
  `0ee77e256c01ad4d03345570959629c1dfc89db0`. 오래된 main과 설치본을 동일시하지 않았다.
- 개발 작업본: `D:/codex-tmp/caspi-connection-owner-20261114`,
  `fix/connection-owner-20261114`. origin/main 기반 격리 작업본에 실제 월계와
  중앙 설치 파일을 먼저 옮겼다. 11/13 실패 종료/새 시도/영수증 검증 보강 보존.
- 월계 `caspi-connection-owner-20261114-wolgye-r1`, 12 Python 파일.
  2026-11-14 **09:43:47 KST** 설치 확인. 서비스 시작 09:43:46.
- 백업: 월계 `/var/backups/caspi/owner-20261114T003949Z`.
  최초 검사 시간 초과 시 서비스 변경 없이 중단했고 이후 전체 이력을 나눠 검사했다.
  기존 전체 약47만 작업의 미완료 쓰기 검사와 lock 내 신규 작업 재검사 통과.
- 중앙 실제 실행본 `/home/sdg/.local/lib/cas-supervisor-20261027-target-recovery-r2`의
  `store_scale_sync.py`, 신규 `caspi_remote_snapshot.py` 및 월계 등록의
  `scale_data_snapshot_backend=caspi_owner`만 반영했다.
  백업은 `~/.local/state/cas-supervisor/code-backups/connection-owner-20261114`.
- 중앙 관리 입구의 활성 작업 검사 후 09:44:45 KST supervisor 재시작 성공.
  사건 `central-restart-7852423f-b32e-4935-8d9b-97ec00909c2a`.

## 동작 변경

1. 기존 CASPi 서비스 내부 소유자가 TCP9600 연결과 공통 flock을 유지한다.
   별도 상시 서비스는 없다. Unix socket은 `/run/lock/caspi-scale.lock.owner.sock`,
   0600/동일 UID peer 검사, 32 client 상한, 메시지/프레임/대기/작업 시간 상한.
2. Bluetooth, SSH CLI, 상품·문구·누계·자동 관측이 로컬 lease로 같은 연결을 쓴다.
   쓰기 전 확인→기대값 검사→증거 저장→송신→ACK→재읽기까지 lease 하나다.
   원장/작업 ID/ACK/BCC/저장/영수증의 기존 성공 조건을 약화시키지 않았다.
3. EOF는 유휴 상태에서 감지하거나 다음 요청 직전에 확인한다. 정상 요청의 고정20초
   sleep이나 깨우기용 조회는 없다. 송신 뒤 실패는 자동 재송신하지 않는다.
   오류·클라이언트 단절은 연결을 폐기하고 실패 기록/미확정 쓰기를 보존한다.
4. 중앙 전체조회는 `caspi.py snapshot`을 사용한다. 검증된 F4240 종료 프레임까지
   읽어야 전체 성공이다. 대상·BCC·중복 PLU·완료 순서·제한을 검사하고 부분 결과는
   게시하지 않는다. 중앙의 기존 snapshot/manifest/기대값 검증을 그대로 통과한다.
   PLU 응답 사이에 현장 요청이 실행될 수 있고 완성된 프레임을 섞지 않는다.
5. 현장 우선/배경 aging, 장애 시 배경 접속 backoff를 둔다. CLI의 owner 장애를
   직접 TCP 우회나 쓰기 재시도로 바꾸지 않는다.
6. V1 relay 연결 스크립트에 `.legacy` intent flock을 추가했다. 진행 중 거래가
   끝난 다음 기존 TCP 연결·잠금을 넘기며 V1 종료 후 다음 요청이 소유권을 회수한다.
   네트워크 주소·Bluetooth 페어링·기존 relay 서비스 설정은 보존했다.
7. Pi 설정 변경은 `connection_owner_enabled=true` 한 항목이다.
   새 앱 배포를 전제로 하지 않는다. 매장 폰 hello/read_updates 요청·응답을 실제 확인했다.

## 검증

- Linux CASPi 관련102건(1건 환경 조건 skip), 중앙/누계/snapshot63건,
  추가 실제 PLU writer를 이용한 모의 TCP 통합1건. 합계165통과/1skip.
- 새 소유자 시험: 동시16요청, 연결 재사용, 유휴 EOF, 송신 후 EOF 무재전송,
  거래 중 EOF, 예상 밖 잔여 데이터, BCC 오류, 전체조회 종료/중간 실패,
  V1 flock 인계, 배경 backoff, owner 부재 시 직접 우회 금지.
- 모의 text writer: 실제 실행기로 사전 읽기/ACK/재읽기 한 연결 확인;
  ACK 유실 때 pending 증거 보존·미확정 오류·단1회 송신 확인.
- 모의 PLU writer: 동일 연결의 사전/사후 읽기, ACK, 변경하지 않은 필드 검증 통과.
- 월계 실제 전체조회1: **76개/종료77번, 20.27초**, 09:44경.
- 중앙 실제 전체조회2: **76개, 19.321초**, captured_at
  `2026-11-14T00:47:14.521208Z`, `verified`, 내용 동일(`writer_action=not-needed`).
  Supabase 관측 갱신까지 기존 경로 통과. snapshot hash
  `cf0a97d56f0c72887b2114826989b3710ab384a0f30b641db3b01c554ab7928d`.
- 실제 광고1/2, 성분4 읽기 성공/BCC 확인(0.413/0.245/0.208초).
  사건 `3c4052be-c18b-48b8-99fa-5fba1823b6cd`,
  `8ce78ca8-59d8-47e2-ae9d-eb0b700e6faa`, `ab3f07aa-5ca5-4a6b-8f97-c67cff603513`.
- 09:48경 설치 이후 누계5회 성공(변화 없음4회 포함), 실패 로그0,
  owner generation1, TCP ESTAB1, NRestarts0. 실제 폰 RFCOMM hello/read_updates 성공.
- 09:51:40 KST 최종 대조: 설치12파일 manifest 일치, 동일 TCP ESTAB1 유지,
  CASPi RSS33,380KiB/3threads. 이 수치는 장기 최대치가 아닌 확인 시점 값이다.
- 증거: `D:/codex-tmp/caspi-owner-stage-20261114`의 manifest, before,
  first-live-snapshot, live-texts, central-installed, central-live-verify, pi-observation JSON.
  원시 값·인증은 공통 이력에 넣지 않는다.

## 한계와 이어갈 일

- 짧은 관측으로 장시간 재발 없음/물리 고장 해결을 단정하지 않는다. 월계 저울
  펌웨어 내부 원인과 외부 프로그램 동시 접속 여부는 여전히 미확인이다.
- 실제 상품/문구 쓰기, 현장 V1 전환, 케이블/전원 차단은 운영 장비에서 유발하지 않았다.
  실제 쓰기는 다음 승인된 업무의 ACK/readback/영수증으로 추가 확인해야 한다.
- 연결 소유자 구조의 월계 한정 canary다. 다른 매장 공통 버전 일치 완료가 아니다.
  공통 배포 도구/버전 감시 기준의12파일 전환과 전 매장 적용은 장시간 관측 후 필요하다.
- 기존 Telegram 이상/복구 발신 정책은 이번 적용에서 바꾸지 않았다. 경고만 숨기는
  해결이 아니다. 지속적인 실제 성공에 기반한 복구 판정 개선은 별도 남아 있다.
- SQL migration, 과거 실패/보류/원장 삭제, 인증·요금·네트워크 변경은 없다.
- 원복 시 새 쓰기 진행 여부와 `.legacy`+공통 lock을 먼저 확보하고 백업 코드/설정/
  relay를 함께 복원한다. 동작 중 owner의 lock을 강제로 해제하거나 raw TCP로 우회하지 않는다.

설계: [연결 소유자 계획](../plans/CASPI_CONNECTION_OWNER_2026-11-12.md).
사전 비교: [다른 매장과 비교](2026-11-14-wolgye-store-comparison.md).

## 소스 기록

- CAS 저장소 커밋: `430833d5510a7a8d9523ed761f0609d65115e60e`. 설치본의 중복 쓰기 방지·새 시도 보호를 보존한 연결 소유자 코드와 테스트를 포함한다.
- Git 소스 기록과 위 실제 설치 해시 검증은 별개 증거다. 다른 매장 배포나 장시간 검증 완료를 뜻하지 않는다.
