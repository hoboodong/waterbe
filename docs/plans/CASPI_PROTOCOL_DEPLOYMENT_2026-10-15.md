# CASPi 프로토콜 개정1 적용 기록

## 범위와 원인

월계 손질낙지 PLU28 광고번호0→1 변경이10:00/10:13KST에 앱 사전 단계에서 실패.
부모 쓰기 ID는 Pi ledger에 없고 앱 오류는 request_rejected로 축약됐다.
Pi 문구 read_text 응답 종류/번호 누락과 앱 필수 검사 사이의 계약 결함을 확인했다.
두 실패의 정확한 예외를 이 결함 하나로 확정하지 않는다. 당시 문구 설정/cache
상태도 영향을 줄 수 있으나 현재 행만으로 과거 상태는 재구성되지 않는다.

## 소스·검증

- CAS 원본 contracts/CASPI_PROTOCOL.md, caspi-v1.json. app docs/CASPI_PROTOCOL.md 연결.
- 동일 벡터를 Python 생산자·중앙 소비자/Dart 소비자가 검사. 종류/번호/정상부재0x99 구별.
- 앱 CASPi77건 통과, 계약5건/변경경로 분석/배포도구12건 통과.
- CAS 깨끗한 최신 기준276115d에서74건 중73통과/1skip, 배포 overlay2건 통과.
  이전 dirty작업본77건 결과와 다른 테스트 수를 혼동하지 않는다.
- Waterbe checker2건 및 양쪽 fixture 내용 일치. 비밀/원시 payload는 Git에 넣지 않는다.
- CAS 소스 b963982(후속 기록 커밋은 별도), 앱 배포 소스 acd6c4e(+2277).

## 운영 적용 (2026-10-15 12:54~12:56 KST)

설치 전 실행 중 쓰기와 실제 저울 lock 확인, 원본 백업. 기존 live-only 수정은
보존하고 문구 결과/hello의 추가 항목만 overlay했다. 설정·WiFi·쓰기가드·ledger 유지.

| 대상 | 결과 | 백업 |
| --- | --- | --- |
| 월계 | text/hello 적용 | /var/backups/caspi/protocol1-20261015T035432948002Z |
| 마포 | text/hello 적용 | /var/backups/caspi/protocol1-20261015T035443458955Z |
| 미아 | text/hello 적용 | /var/backups/caspi/protocol1-20261015T035449340041Z |
| 왕십리 | 누락 caspi_text/reader 모듈 추가 및 hello 적용 | /var/backups/caspi/protocol1-20261015T035610143013Z |
| 문어팀 | SSH 접속 불가, 변경 없음 | 없음 |

중앙 실행본 /home/sdg/.local/lib/cas-supervisor-20261012-http5xx/scale-data/tools/
caspi_remote_text.py에 같은 대상 식별 검사를 적용했다. 백업:
/home/sdg/.local/state/cas-central/protocol-backups/protocol1-20261015T035457918527Z.
기존 중앙관리 사전 검증 후 supervisor 재시작, 공통 사건
central-restart-7b3f735e-080b-4582-aa80-7fcc674aca04 성공. 다른 워커 재시작 없음.

## 실제 확인과 한계

- 네 매장 중앙→CASPi→저울 광고1번 조회가 종류/번호·BCC·payload hash 검사 통과.
- 네 매장 hello 개정1/고정 매장/쓰기 가능/문구 명령 지원 확인.
- 월계 PLU28은 과거 검증된 record위치를 재사용해 현재 저울을 읽는 쓰기 preview 실행.
  광고번호는 이미1이며 mode=unchanged, 변경 필드0, 실제 쓰기 없음.
- 예전 실패 요청 재전송/새 business write/기존 영수증·작업함 상태 재작성 없음.
- 폰 Bluetooth 왕복·+2277 실제 설치·새 요청의 ACK/read-back은 현장 미검증.
- 문어팀은 접속 복구 뒤 같은 설치/조회 필요. 현재 전체 매장 완료로 보고하지 않는다.

## APK 공개 배포

+2277 표준 배포 진행 중. 완료 시 공개 versionCode/sourceCommit/APK bytes·hash/잠금
해제 결과를 여기에 추가한다. 빌드 중 상태는 배포 완료가 아니다.
