# 미아점 저울 광고문구 2번 변경

## 요청과 결과

- 2026-11-06 사용자 요청: 광고문구 2번 `*랩 : PO`를 `*랩 : PE`로 변경.
- 원래 작업 ID: `24f87a1d-af65-4eba-9b0e-2694203357c5`.
- 21:05 KST 첫 MCP 변경 요청은 HTTP 403으로 접수되지 않았다. 원래 작업의 CASPi 영수증도 `not_found`였고, 21:05:51 KST 실제 저울 재읽기 값은 `*랩 : PO`였다.
- 원인은 중앙 `service_role`에 `request_scale_text_change_idempotent` 실행 권한과 `scale_text_change_requests` 조회 권한이 없는 것이었다. 권한 조회에서 두 항목 모두 `false`였고 HTTP 응답은 각각 `permission denied`를 반환했다.
- 21:10 KST 필요한 두 권한만 운영 DB에 부여했다. 같은 작업 ID와 원래 기대값으로 요청을 접수했으며 새 변경 ID로 중복 제출하지 않았다.
- 저울 작업 요청 `b730ddfd-3dda-4e6e-adf7-d4f48e232c1f`는 21:12:01 KST `succeeded`, 실제 문구 `*랩 : PE`, 실패 코드 없음으로 종료했다.
- 21:12:13 KST 별도 CASPi `read_text` 재읽기에서 광고문구 2번 `*랩 : PE`, BCC 정상 확인. 읽기 작업 ID `50d99e04-9ce2-4115-9b58-2753a1c25ab4`.
- Supabase `scale_text_snapshots`의 미아 광고문구 2번도 `*랩 : PE`, captured_at 21:12:01 KST로 확인했다. 휴대폰 실제 수신과 실물 라벨 출력은 확인하지 않았다.

## 재발 방지와 상태 구분

- 시코드 마이그레이션 `20261106000001_scale_text_service_role_access.sql`에 중앙 서비스 계정의 함수 실행·작업 상태 조회 권한을 기록했다. 운영 DB 권한 적용과 Git 마이그레이션 기록은 별도 단계다.
- 워터비 MCP의 원래 작업 결과는 최초 HTTP 실패로 `execution_unknown`을 보존한다. 이후 같은 ID로 생성된 저울 요청 행의 성공과 독립 재읽기·스냅샷이 실제 완료 증거다. 최초 MCP 오류 기록을 성공으로 재작성하지 않는다.
- 관련 지침: [상품 데이터 점검](../guides/PRODUCT_DATA_AUDIT_GUIDE.md), [시코드·저울 연결](../guides/SEACODE_SCALE_GUIDE.md).
