# 매출 데이터 작업 공간

이 폴더는 워터비 매출 질문과 매출 원천 데이터를 다루는 전용 진입점이다.

## 구조

- `wangsimni.yaml`: 왕십리점 수기 매출 기록.
- `mapo.yaml`: 마포점 수기 매출 기록.
- `wolgye.yaml`: 월계점 수기 매출 기록.
- `namseon/`: 남선매출 Google Drive 자료를 누적한 SQLite 작업 공간.

## 매출 질문 처리 규칙

매출 관련 질문을 받으면 먼저 이 폴더를 기준으로 판단한다.

1. 남선매출, Google Drive, 월 매출, 매장별 매출, 상품 제외 매출을 묻는 경우 `namseon/namseon_sales.db`와 `scripts/namseon_sales.py`를 사용한다.
2. 일별 Google Drive 파일이 새로 추가됐다고 판단되면 먼저 `scripts/namseon_drive_sync.py --incremental --trash-duplicates --upload-db`로 DB를 갱신한다.
3. 같은 날짜 파일은 하나만 사용한다. `scripts/namseon_drive_sync.py`가 Google Sheets 파일과 최신 수정 시간을 기준으로 선택한다.
4. `낙지볶음`, `갑오징어볶음`처럼 특정 상품 제외 요청이 있으면 `month-total --exclude` 옵션을 사용한다.
5. 사용자가 "20% 더해진 금액"처럼 수수료 차감 전 금액을 물으면, 차감 후 금액을 `0.8`로 나눈 값을 기준으로 답한다.

## 자주 쓰는 명령

```bash
python3 scripts/namseon_sales.py month-total --store mapo --month 2026-05
python3 scripts/namseon_sales.py month-total --store wangsimni --month 2026-05 --exclude 낙지볶음 --exclude 갑오징어볶음
python3 scripts/namseon_drive_sync.py --incremental --trash-duplicates --upload-db
```

`*.db`, `*.db-shm`, `*.db-wal` 파일은 로컬/Drive 작업 산출물이며 git에 올리지 않는다.
