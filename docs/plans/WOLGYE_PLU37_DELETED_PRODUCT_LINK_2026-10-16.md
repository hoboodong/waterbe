# 월계 PLU37 삭제 상품 연결 잔존 조사

## 확인 원본

- 2026-10-16 현재 호스트 Supabase CLI 인증으로 REST 조회.
- 대상 `wolgye` / PLU37 / 상품 `p_wolgey_jeonbok_002`.
- 상품 `is_active=false`, `is_operating=true`, 수정시각 `2026-10-16T03:18:22.661567+00:00`.
- 상품 삭제 후 서버 binding의 `deleted_at=null` 잔존 확인.
- 삭제 DAO는 binding을 hard-delete하여 서버 해제 전달이 누락된다. SQLite의
  전체 PLU 유일 제약도 새 연결 생성 시 해제 tombstone을 replace로 제거할 수 있다.

## 변경 전 연결 원본 (복구 근거)

```json
{"id":"product-scale:wolgye:p_wolgey_jeonbok_002","store_id":"wolgye","product_id":"p_wolgey_jeonbok_002","plu_number":37,"department_number":1,"field_rules":["productName","productCode","representativeQuality","retailPrice"],"initial_authority":"scale","status":"initializing","auto_apply_enabled":false,"last_synced_values":{},"last_snapshot_sha256":"2a1c2f8b8eed8945b81403f7215848201ab646d8e2e415d767d1283372092b64","last_synced_at":null,"updated_at":"2026-10-16T03:18:00.783+00:00","deleted_at":null}
```

## 제한된 복구

- 상품 비활성 재확인 후 binding의 ID/매장/상품/PLU/원래 updated_at/deleted_at을
  모두 조건으로 사용하는 PATCH로 `deleted_at`·`updated_at`만 변경한다.
- 변경 행 1건 반환과 live PLU 재조회로 확인한다. 실패/동시 수정이면 재쓰기하지 않는다.
- 저울 쓰기·상품 삭제/재생성·기존 작업 재전송 없음. 실제 폰 로컬 캐시 반영은 별도.
- 최초 service-role PATCH는 403으로 거절되어 변경되지 않았다. 권한/RLS를 확장하지 않고,
  기존 앱 anon 역할의 `x-store-id=wolgye` 정책으로 같은 조건부 변경을 수행했다.
- 2026-10-16T05:25:55.466296+00:00 두 시각 필드 변경 1건 반환 확인.
  이어진 `store_id=wolgye & plu_number=37 & deleted_at IS NULL` 조회 결과는 0건.
  연결 원본은 tombstone으로 보존되어 있다. 실제 앱 재연결 완료는 미확인.

## 재발 방지 소스 (아직 미배포)

- 상품 개별/일괄 삭제와 연결 해제를 같은 트랜잭션의 pending tombstone으로 저장.
- SQLite v63은 전체 행을 보존하며 PLU 유일성을 live 행에만 적용. 기존 필드/실패 증거 보존.
- 삭제가 확인된 상품 연결만 복구 정리. 단순 snapshot 부재·운영중 off는 자동 해제하지 않음.
- 서버에는 해제 기록을 먼저 전송하고 새 연결을 나중 전송. 실패 때 미전달 기록 보존.
- 서버 snapshot 수신 뒤에도 삭제 상품의 옛 live 연결을 해제 대상으로 보존.
- 관련 회귀33건 및 실제 provider v62→v63 업그레이드1건 통과.
- 확대 회귀의 기존 상품 연결 UI1건과 저장소 격리10건 실패는 기존 검증 문서에
  동일 이름으로 기록된 실패다. 전체 회귀 정상으로 보고하지 않는다.
  앱 문서 `docs/STRUCTURE_REFACTOR_VERIFICATION_2026-10-15.md` 참조.

## 커밋·푸시

- 사용자 푸시 요청으로 시코드 `1fc72ae07c564b9180c0c0f21c864e39e648403a`를
  origin/main에 게시하고 원격 커밋 일치를 확인했다.
- 앱 소스/테스트/지침14파일만 포함. 기존 생성파일·다른 변경은 보존했다.
- APK 배포는 하지 않았다. 공개 앱은 기존 +2280이며 이 재연결 보완 소스는 미배포다.

## 2026-10-17 후속 앱 적용

- 사용자 배포 요청으로 시코드 `1.0.4+2281` / Android4281 / 소스
  `bffba483ed4647675e7c3b30e8b42d9eeceef9cd` 공개 배포 완료.
- 재연결 보완과 compact PLU 상세 UI 포함. 추가 회귀30건/실제 v62→63 이관1건 및
  표준 배포 필수 검사 통과. 공개 APK24,038,669bytes 독립 다운로드/해시 일치.
- SHA256 `eb70564cbb75681492c5cde7c2ca83915ce90d660fef7e94fcbe5f5783da1ef4`.
  잠금 부재 확인. 실제 월계 폰 설치·37번 재연결 완료는 미확인이다.
