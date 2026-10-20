# 저울 실제값 관측 확장 운영 적용

사용자 승인: 2026-10-20 “응 전부”. 범위는 CASPi·씽크패드 중앙·수파.
앱 공개 배포와 실제 저울 업무값 변경은 포함하지 않는다.

## 적용

| 대상 | 적용 내용 | 보존 근거 |
| --- | --- | --- |
| 미아 | 상품 76개·참조 문구 3개 관측, 선택적 문구 피드 | `/var/backups/caspi/observations-20261020T094010Z` |
| 마포 | 상품 81개·참조 문구 5개 관측 | `/var/backups/caspi/observations-20261020T094224Z` |
| 월계 | 상품 76개·참조 문구 3개 관측 | `/var/backups/caspi/observations-20261020T094411Z` |
| 왕십리 | 상품 76개·참조 문구 4개 관측 | `/var/backups/caspi/observations-20261020T094226Z` |
| 문어팀 | SSH 시간 초과, 적용하지 않음 | 기존 설정·기록 유지 |
| 중앙 | 네 매장 등록, 변경분 게시·매장별 실패 분리·과거 부적합 영수증 격리 | `/home/sdg/.local/state/cas-central/observation-backup-20261020T094122Z` |
| 수파 | `latest_caspi_text_receipts(text)` 추가, invoker/RLS 유지 | 앱 migration `20261020000001_caspi_text_observation_index.sql` |

저울 네트워크·Bluetooth 페어링·쓰기 허용·업무값·기존 미확정 작업은 변경하지 않았다.
월계 최초 설치는 저울 lock 사용 중이라 변경 전 중단했고, 통신이 끝나는 시점에
재시도하여 적용했다. 운영 DB는 SQLite 온라인 백업과 integrity_check를 거쳤다.
전체 레코드 위치는 당일 중앙 snapshot의 manifest/hash/BCC로 검증했다.
PLU 번호를 record 번호로 추정하지 않았다.

## 실행본

- CASPi: `/opt/caspi/{caspi.py,caspi_bluetooth.py,caspi_read_feed.py}`.
- SHA-256:
  - caspi.py: `1dee925f11ec7087dad4d6479b4a1ab06a579df8b4c028c22848b17808f1dfc3`
  - caspi_bluetooth.py: `118706a33b854d71202c89389e699d53ba489707515ae6cbdfc3cfdf7a1fe263`
  - caspi_read_feed.py: `478b77a36845733249038819bd5aec026c32e3dbda810ac2e4c5f732afdf496c`
- 중앙: `/home/sdg/.local/lib/cas-observations-20261020-v3/caspi_receipt_sync.py`.
  기존 service의 인증 환경을 유지하고 `zz-observations.conf`로 실행본만 지정한다.
  기존 `resilient.conf`가 새 override보다 뒤에 정렬되어 구 실행본을 선택한 것을
  확인하여 override 이름을 정정했다. 그때의 설정 오류는 이후 실행본 교체와 구별한다.
- 원격보다 뒤인 로컬 CAS checkout을 통째로 배포하지 않았다. 원격 및 live 소스와
  세 파일의 diff를 대조한 뒤 manifest hash가 일치하는 파일만 교체했다.

## 중앙 전달 복구

기존 receipt-config에는 문어팀만 있었다. 네 매장을 추가하고 문어팀은 삭제하지 않았다.
`publish_observation_changes=true`, 페이지 500개, 회차당 최대 8페이지로 제한한다.
같은 회차에서 접속 실패 매장은 반복해서 호출하지 않는다.

월계·왕십리 과거 영수증 일부에는 원래 요청이 없었고, 월계에는 폐기된
`aggregate_hours` 명령도 있었다. 이들은 `receipt_quarantine`에 원문과 이유를
보존하는 트랜잭션을 완료한 뒤 수신 커서를 진행한다. 게시 성공으로 표시하지 않고
저울 명령을 재실행하지 않는다. 전송 오류·ACK 불일치의 커서는 여전히 보존한다.

## 검증

- CASPi Python 84건 중 83건 통과, 기존 조건 1건 skip.
- 앱 상품 연결·저울 화면 회귀 테스트 27건 모두 통과.
- 네 매장 설치 hash, service ready/write_enabled 유지 확인.
- 구 read_updates 응답에는 PLU만 있고, 새 capability opt-in에만 문구 목록 추가.
- 18:51:55 KST: 네 매장에서 실제 관측한 상품·문구 각 1건, 총 8건을
  기존 중앙 publisher로 게시하고 동일 ID/hash ACK 확인. 물리 쓰기 0건.
  근거: 중앙 백업 폴더 `publication-canary.json`.
- 수파 익명 함수 실행 권한 없음, authenticated 허용·RLS invoker 확인.
  기존 상품 RPC를 수정하지 않았다.
- 공통 운영 이력에 `caspi-observations-20261020-operational-v3` 기록 저장 확인.
  이 기록 자체의 클라우드 전파 완료를 의미하지 않는다.

## 미완료·한계

- 과거 영수증 초기 처리 진행 중. canary 성공과 전체 backlog 완료는 다르다.
- 실제 두 휴대폰 Bluetooth 왕복/설치/화면 동기화는 현장 검증 전.
- 신규 앱의 실제값 UI·상품 중재는 소스 상태이며 기존 앱에 자동 설치되지 않는다.
- 문어팀 접속 불가. 새 PLU 자동 발견과 삭제 전체 탐지는 이 피드 범위 밖이다.
- 배경은 상품별 2초 이상 간격으로 순환하고 현장 작업에 양보한다.
  전체 상품을 2초마다 모두 확인한다는 뜻이 아니며 변화 없는 영수증은 공유 반복 게시하지 않는다.
