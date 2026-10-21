# 시코드 지연·멈춤 진단 — 2026-10-21

## 조사 범위

사용자 요청은 원인 분석이다. 코드·서버 진단 SELECT·중앙 상태만 확인했고
작업 취소/재전송·DB 수정·앱 수정·배포는 하지 않았다. ADB 연결 폰이 없어
현장 프레임 시간·ANR·메모리·설치 버전은 측정하지 못했다.

공개 latest.json: 1.0.4+2286, 실제 versionCode4286,
sourceCommit dff55e03611d4829f094264f82f94397f03fe3b2.
시코드 origin/main 4a1b4f8은 위 배포 커밋 이후 GUILD 문서만 변경됐다.
Windows D:/dev/seacode_new는357ef69의 dirty 작업본이라 자동 갱신하지 않고
git show origin/main으로 배포 계열 코드를 읽었다. OneDrive의 구 작업본은 분석에서 제외했다.

## 확정 관찰: 월계 PLU37 대기 반복

- 원래 작업ID 2a699450-7870-45e4-a0ee-a3e78fedffa5.
- local_work_observed는 10월18일18:43:17KST, 광고번호0→1 요청,
  status waiting/request_id null. 당시 관찰이며 현재 전체 작업상태를 대체하지 않는다.
- 10월21일00:00~18:55:42KST 서버 수신 진단에서 같은ID/대상37의
  route_selected와 text_dependency가 각각7964건이다. route bluetooth.
- 연속 조회 사이에도 각 단계가7932→7964건 증가했고 약2초 간격 반복과 부합한다.
- 코드 scale_change_outbox_coordinator.dart:129의2초 타이머가 retryTransmission→resume를 호출.
  queued 상태의 작업은 _dispatch로 가고 route를 다시 put한 뒤 route_selected를 기록한다.
- _dispatch는 문구 의존 검사를 실행하며 ScaleDependencyPending이면
  text_dependency를 기록하고 작업 상태는 queued로 남긴다. 다음 주기에 같은 경로를 반복한다.
- scale_product_text_dependencies.dart는 prior.isPending이면 의존 대기 예외를 낸다.
  해당 문구 자식작업이 실제 왜 끝나지 않았는지까지 이번 조사에서 확정하지 않았다.

이는 저울에 실제 변경 명령을7964번 보냈다는 뜻이 아니다. dispatch_started 이전의
문구 의존 확인 단계 반복이다. 하지만 불필요한 로컬 쓰기·진단 저장·전송·상태 갱신을 만든다.
실제 멈춤의 유일한 원인 확정이 아니라 운영에서 확인된 우선 수정 대상이다.

## 코드상 누적 비용

### CASPi 이력 전체 JSON 재직렬화

caspi_operation_repository.dart의 SharedPreferencesCaspiOperationRepository는
caspi_readonly_operation_outbox_v1 하나에 모든 작업을 보관한다.
get/listForStore/pendingPublications는 jsonDecode로 전체를 읽고,
_put은 전체를 읽어 한 건을 바꾼 다음 jsonEncode+setString으로 전체를 다시 쓴다.
선택된 구현에 완료 이력의 크기 제한·분리 보관 경로는 없다.

pollReadUpdates는 수신 영수증마다 get과 put을 반복한다.
작업 revision마다 receipt sync도 깨워진다(실행 중 중복 방지 guard는 있음).
10초 유지보수 후 변경이 없어도 reloadLocalWrites가 호출되며,
_withLocalWrites는 매장 전체 이력을 파싱·정렬하고 작업별 상품 목록을 순회한다.
누적 건수와 payload 크기에 따라 메인 isolate의 직렬화·객체 생성 비용이 커질 수 있다.
실제 폰의 JSON 바이트 수와 실행 시간은 아직 미측정이다.

### 작업함 반복 전체 읽기·표시 갱신

_run은 전체 목록을 여러 번 읽고 queued 항목마다 blockers 조회를 반복한다.
SqliteScaleChangeOutboxStore.listForStore는 만료 완료행 정리 DELETE와 전체 목록 SELECT를 한다.
_refreshState는 매번 항목 상세 JSON을 만들고 동일 상태여도 새 state를 발행한다.
여기에2초 재시도와 의존 대기가 결합하면 변화 없는 업무에도 비용이 발생한다.

### 화면 새로고침도 전체 snapshot

sync_coordinator.dart의 syncModules는 요청한 화면 모듈만 확인하는 것처럼 보이지만
마지막에 downloadFullSnapshot을 호출한다. snapshot_sync_operations.dart는15개 자료군을
동시에 조회하며90일 출력 기록의 print_payload도 요청한다.
_replaceLocalSnapshot은 SQLite 트랜잭션에서 삭제/행별 삽입으로 교체한다.
이는 화면별 새로고침·초기 시작·매장 전환에서 긴 로딩/DB 경합을 만들 후보이며,
사용자 증상 시점에 실제 실행됐다는 기록은 아직 확보하지 못했다.
평소 저장/출력 자동동기화는 uploadAll이므로 모든 출력마다 전체 다운로드한다고는 하지 않는다.

## 서버·장치 상태와 한계

18:53KST 제한 점검: Supabase ACTIVE_HEALTHY, 연결25, 대기잠금0.
중앙 history/read/supervisor 실행 중이고4개 매장 CASPi 누계 관측8~43초 이내.
문어팀은 접속불가. 과거10월12일500오류를 현재 장애로 해석하지 않았다.
이 결과는 수파 I/O 예산·앱 REST 전체 성능·휴대폰 UI 정상의 증거가 아니다.

오늘 실패 진단 집계에는 미아 store_settings timeout1건과 왕십리 printer 실패1건이 있다.
미계측·오프라인·ANR 직전 미전송 사건은 서버 기록에 안 보일 수 있다.

## 우선순위와 후속 검증

1. 같은 문구 의존 대기는 새 변화/자식 완료/연결 변화에 반응시키고 반복 진단을 억제.
   한 대상만 대기로 두며 다른 업무와 사용자 입력은 계속 가능해야 한다.
   원래 작업ID/기록을 삭제하거나 재쓰기하지 않는다.
2. CASPi 이력을 건별·색인 기반 저장/최신값 투영으로 분리하는 방안을 설계.
   기존 데이터 보존·오프라인·구버전 호환을 먼저 검증한다.
3. 동일 상태의 목록 재계산과 UI state 발행을 줄이고 전경/백그라운드 busy를 분리.
4. 화면 단위 변경분 읽기와 전체 snapshot을 구분하되 미전송 데이터 보존 계약 유지.
5. 실제 증상 폰의 버전·화면·시각·메모리·프레임 지연/ANR·로컬 이력 크기를 수집해
   각 후보의 시간을 측정해야 현장 멈춤의 직접 원인을 확정할 수 있다.

위 항목은 최초 진단 시점의 상태다. 후속 구현은 아래와 같다.

## 후속 성능 개선 구현·검증

- 사용자 해결 요청에 따라 최신 origin/main `4a1b4f8` 기준 별도 앱 작업 트리
  `D:/codex-tmp/seacode-performance-20261021`에서 구현했다.
  기존 `D:/dev/seacode_new`의 사용자 변경과 뒤처진 HEAD는 보존했다.
- 변화 없는 문구 대기의 반복 처리/진단, 동일 상태 화면 발행, 빈 Bluetooth feed의
  전체 overlay 재계산을 억제했다. 변화/직접 재시도는 재개한다.
- CASPi 전체 JSON 재파싱/재저장 대신 건별 SQLite와 최신값 색인 조회를 사용한다.
  기존 이력/미확정 작업/원본 JSON/손상 자료를 보존한다. 게시 대기는 매장별 제한과
  실패 회전으로 다른 작업을 계속 처리한다. 물리 저울 쓰기 계약은 유지한다.
- 중첩 새로고침을 억제하고 출력기록 저장을 100건 batch로 처리한다.
- 회귀 303건 통과/기존 1건 건너뜀. 마지막 추가 변경의 집중 검증도
  38건 통과/동일 1건 건너뜀. 상세: 앱 `docs/APP_PERFORMANCE_GUIDE.md`, `GUILD.md`.
- 앱 배포/설치 전 현장 폰에는 반영되지 않는다. 실제 폰 장시간 프레임·메모리·ANR
  검증과 부분 다운로드 설계는 남았다. 운영 작업 삭제/강제 완료/저울 변경은 하지 않았다.
- 후속 사용자 배포 요청으로 앱 소스 `3d80495a6e86c02a1df2c4e9f86c968c18b94102`
  기준 +2287/versionCode4287 공개 배포 완료. 공개 APK 24,073,774 bytes,
  SHA256 `df8579b8d497e1125b8fd117ed92a3492d135d118889e3728d95408be668279e`
  로컬/독립 다운로드 일치, latest.json/sourceCommit 및 잠금 부재 확인.
  첫 빌드의 PC native 메모리 부족은 업로드 전에 실패했으며 빌드 메모리 제한 보완 후
  재빌드 성공했다. 상세 실패/복구/검증은 앱 GUILD.md에 남겼다.
- 실제 폰 설치/장시간 검증은 아직 미확인. 후속 사용자 푸시 요청으로 앱 소스와
  배포 기록 및 이 진단 기록을 각 저장소 origin/main에 게시한다.
