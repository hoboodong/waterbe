# 전체 운영 기록·추적 공통 지침

## 책임과 현재 상태

2026-10-05 부분 이전: 공통 기록 수집의 현재 실행 주체는 씽크패드
`waterbe-history.service`, DB `/home/sdg/.local/state/waterbe-history/operations.db`다.
Windows `WaterbeOperationHistory`는 중지/비활성화하고 원복용 DB를 보존했다.
다른 중앙 워커와 Telegram reporter도 씽크패드로 이전했다. Windows 임시 bridge는
중지했으며 native 건강 로그를 씽크패드 reporter가 직접 소비한다. 중앙 실행 상태
관측도 기존 내구성 사건/notice에 연결한다. 기존 Telegram 전달 미확정1건은 보존한다.
상세 전환 증거/남은 항목은 [중앙 이전 기록](../plans/THINKPAD_CENTRAL_MIGRATION.md)을 따른다.
아래 최초 설치 설명과 구 Windows 명령은 이전 이력이며 현재 가동 주체와 구별한다.

워터비가 공통 계약·조회·교차 출처 분석을 총괄한다. 각 프로그램이 자기 원본과
작업 증거를 기록하고 중앙 기록 관리 기능에 전달한다. 매장별 워커를 만들지 않는다.
시코드(상품·할인·생산), 카스씨엘/CASPi(저울·문구·수집), 매출 수집기(남선·대영),
워터비(레시피·원가·보정), 배포 프로그램(소스·버전·해시·검증)이 생산자다.

2026-10-05: 중앙 Supabase `waterbe_operation_history` 및 service-role 전용 추가 RPC,
`waterbe_history_worker_status` 설치. 기존 중앙 Windows PC의 `WaterbeOperationHistory`
작업이 `D:/WaterbeRuntime/operations.db`의 내구성 전달 큐로 수집·전송한다.
공통 `waterbe_api.py call history.read/history.status`로 다른 인증된 호스트도 같은
중앙 기록을 조회한다. 현장 앱/CASPi 원본을 변경하거나 기존 수집기를 대체하지 않는다.

연결 범위: 5개 매장 상품/출력·할인/저울 상품 스냅샷, 공통 저울 문구 스냅샷,
앱 작동 진단, CASPi 게시 영수증, 남선·대영 매출 원본 버전, 워터비 master YAML
파일 버전, 공개 앱 배포 포인터. 파일 버전 감지는 레시피의 개별 재료 변경 해석이 아니다.
배포 포인터 관찰은 APK 검증·휴대폰 설치 완료가 아니다. 앱 모든 동작 계측은 미완료다.

수집은 현재 관찰 방식이다. 한 회차 뒤 60초 대기하고 다음 회차를 시작하므로 회차
소요시간만큼 추가 지연된다. 중간에 A→B→A로 바뀌면 놓칠 수 있다. 업무 행 삭제,
직접 저울 조작의 정확한 발생시각/행위자, 조회 불가 라벨 양식·공통 업소명은
아직 자동 증명하지 못한다. 저울 스냅샷 수집 성공과 물리 저울 최신 확인은 다르다.
광고/성분 스냅샷이 오래됐으면 오래된 자료임을 그대로 알려야 한다.

기존 Telegram reporter에 waterbe_history_health 실패/재개 알림을 연결·설치했다.
동일 출처 2회 연속 실패부터 한 번 알리고 성공 시 재개를 알린다. 메시지 전달
미확정은 기존 전송함 격리를 따르며 성공으로 바꾸지 않는다. 중앙 PC 자체가 꺼진
상황은 이 워커가 스스로 알릴 수 없고 별도 호스트 감시가 필요하다.

## 채팅에 의존하지 않는 조사 순서

1. 공통 API 카탈로그에서 담당·원본·기록 범위·구현 상태를 확인한다.
2. 매장/기능/대상/기간/작업 ID로 중앙 기록을 조회한다. 조회 요청으로 수집·쓰기하지 않는다.
3. 발생시각·관측시각·수신시각을 구별하고 변경 전후 및 증거를 원본과 대조한다.
4. 연결된 작업 ID가 없으면 `경로 미확인`이다. 직접 조작·특정 직원 책임으로 단정하지 않는다.
5. 기록 공백·미연결·권한 실패를 표시한다. 기록 없음은 변경 없음이나 매출 0이 아니다.
6. 원인 확정/가능성/미확인을 구별해 보고한다. 임의 복구·재쓰기·원본 삭제는 하지 않는다.

## 사건 계약

- `(source,event_id)`는 생산자가 정한 불변 식별자. 동일 사건 재전송은 중복 저장하지 않는다.
  다른 내용으로 같은 ID가 오면 거절하고 원본을 보존한다. 진행 단계마다 새 사건 ID를 쓰고
  같은 `operation_id`로 요청→실행→검증→게시를 연결한다.
- `kind`: request/result/observation/change/incident/recovery.
- `result`: pending/succeeded/failed/uncertain/observed. 요청 접수는 실제 성공이 아니다.
- 필수: event_id/source/kind/result/feature/target/observed_at.
  선택: store/operation_id/actor/route/rule_version/occurred_at/last_confirmed_at.
- `occurred_at`: 출처에서 확인된 발생시각. 모르면 생략한다.
  `last_confirmed_at`~`observed_at`: 마지막 확인부터 변경 발견까지의 구간.
  `received_at`: 중앙 수신시각. 늦게 수신해도 발생시각을 덮지 않는다.
- `changes`: 승인된 업무 필드의 field/before/after 배열. 원본을 수정하는 명령이 아니다.
  `evidence_ids`: 접근 통제된 원본 저장소의 불투명 ID. 내용 해시는 무결성 확인이며
  실제 저울 적용·매출 정확성 증명이나 사용자 인증을 대신하지 않는다.
- 성공/복구 결과는 증거 ID를 요구한다. 증거가 있다는 사실만으로 진위가 검증되는 것은 아니다.
- 비밀번호·키·토큰·헤더·원시 오류·고객 개인정보·서명 URL을 넣지 않는다.
  생산자에서 허용된 업무 정보만 추출한다. 필드 허용목록은 문자열 내부 비밀까지
  자동 검출하지 못하므로 무가공 로그를 이 API에 보내면 안 된다.
- 저장은 추가 전용, UPDATE/DELETE 차단. 검산/보정은 새 사건으로 원본을 참조한다.
  일부 실패는 해당 사건을 출처의 내구성 큐에 보존하고 다른 처리를 계속한다.
  큐 전진은 저장 ACK 뒤에만 한다. history_worker는 사건/관측 상태/전달 큐를 같은
  SQLite 트랜잭션으로 보존하고 전송 미확정은 같은 사건 ID로 재전송한다. 영구 실패가
  뒤 기록을 막지 않도록 시도 횟수로 전송 순서를 회전한다. 잘못된 투영은 격리 목록에
  원본 식별자를 남기며 업무 원본은 출처에 보존한다. raw 응답/인증정보는 저장하지 않는다.

## 공통 실행 입구

명시한 중앙 DB 또는 환경변수 `WATERBE_HISTORY_DB`만 사용한다. 다른 프로젝트
비밀 설정을 찾아 복사하지 않는다. DB/원시 증거는 Git에 넣지 않는다.

```powershell
python scripts/waterbe_api.py call history.status
python scripts/waterbe_api.py call history.read --store wangsimni --feature scale.product --date 2026-10-05
python scripts/operation_history.py --database D:/WaterbeRuntime/operations.db append --event-file approved-event.json
python scripts/operation_history.py --database D:/WaterbeRuntime/operations.db query --store wangsimni --feature scale.product --since 2026-10-05T00:00:00+09:00
```

query는 저장소를 만들거나 원본을 변경하지 않는다. sequence 기반 next_after/has_more로
모든 페이지를 조회한다. 시간 필터는 observed_at 기준이다. append는 명시적 기록 요청이며
저울/앱/매출/레시피를 변경하지 않는다. CLI는 인증 서버가 아니므로 중앙 운영 전에
OS 접근 권한·출처 인증을 유지한다. 중앙 API는 service-role 전용이며 익명/일반 앱
조회·추가 권한이 없다. 사용자 로그인별 세분화 API는 미구현이다. 키를 대화나 Git에
넣지 않고 호스트의 기존 사용자 환경 설정만 사용한다. 개인별 행위자 인증을 뜻하지 않는다.

중앙 실행/점검:

```powershell
python scripts/history_worker.py --database D:/WaterbeRuntime/operations.db status
python scripts/history_worker.py --database D:/WaterbeRuntime/operations.db drain
./scripts/install_history_worker.ps1
```

installer는 원본 3개 파일 해시로 불변 릴리스를 만들고 자기 작업만 교체한다.
로그인한 현재 사용자로 실행하며 로그아웃/전원 종료 때 상시 실행을 보장하지 않는다.
SQLite 일일 온라인 백업은 `D:/WaterbeRuntime/backups/YYYYMMDD/operations.db`에
보존하고 integrity_check 및 별도 읽기 복원 시험을 통과했다. 보존기간/자동 삭제는 없다.
공용 Supabase의 외부 백업·개인별 인증·로그아웃 상태 서비스는 별도 운영 과제다.

## 연결 구현 순서와 완료 조건

1. 공통 저장/조회 계약과 중복·충돌·불변성·시간·개인정보 경계 검증 (중앙 적용).
2. 기존 시코드 진단, 게시 영수증, 매출 원본 버전에 관측 어댑터 연결 (중앙 적용).
3. 상품 및 성분/광고문구의 이전 버전 보존. 읽을 수 있는 라벨 양식·공통 설정도
   포함하고 미지원 필드는 감시 불가로 표시. 공통 설정과 상품 설정을 구별한다.
4. 중앙 설치·인증·백업·내구성 전달 큐·누락 점검·미해결 사건 및 중복 억제 알림.
5. 레시피/원가 파일·할인 출력·배포 포인터 기록 연결. 후속: 파일의 필드별 해석,
   출처 자체의 모든 변경 사건 보존(관측 사이 변경 포함), 독립 호스트 장애 감시,
   아직 제공되지 않는 물리 저울 설정·앱 세부 행동의 계측.

완료는 문서·코드 작성이 아니다. 실제 생산자 사건 수신, 중단 후 재전송, 중복 방지,
비밀 미노출, 미연결 표시, 권한 제한, 원본 근거 추적 및 알림/복구 검증이 필요하다.
서버·앱·장비 배포 여부를 각각 보고하며 앱 배포는 사용자 요청 때만 수행한다.
