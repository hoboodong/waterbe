# 수파 부하 축소 — 2026-10-13

## 확인 근거

- DB 누적 통계에서 출력기록5천회/매장, CASPi 영수증 약5천회 조회가 관측됐다.
  평균 실행시간 각각 0.65~1.55초/1.88초. 통계 시작 시각 미확인으로 일별 건수는 아니다.
- `latest_caspi_product_receipts`는 누적 임시 블록 쓰기371649가 관측됐다.
  disk I/O 예산 잔량은 미확인. 정상 응답을 예산 정상으로 대신하지 않는다.
- 출력 기록 updated_at과 영수증 published_at 인덱스가 없었다.

## 조치

- 기존 dirty 작업은 보존. 이력 관측만 5분 간격, 변경분 clock+identity 정렬.
- 기존 운영 설치본 복사 후 위 두 변경만 적용. 서비스 drop-in zzz-low-io.conf.
- 재시작 사건 `central-restart-0d2761cf-71ca-4d94-83c8-e0d3ccbd6ca4`,
  10:43:04 KST active. 로컬 history 회귀18개 통과.
- 인덱스 실행 원본: `scripts/sql/20261013_history_low_io_indexes.sql`.
  업무 데이터 삭제, 통계 초기화, 유료 증설, 앱 배포 없음.

## 남은 검증

- 7개 인덱스 모두 indisvalid/indisready=true 확인 완료.
- 새 관측 성공, 이후 실제 요청 지연/쿼리 호출 차분 측정.
- 최신 상품 영수증 RPC의 누적 JSON 정렬을 캐시/투영으로 바꾸는 것은 별도 후속.
- 중앙 자체 원본 사건으로 이력 수집을 완전히 대체한 것이 아니다.
