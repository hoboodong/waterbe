# 매출 데이터 작업 공간

이 폴더는 워터비 매출 질문과 매출 원천 데이터를 다루는 전용 진입점이다.

## 구조

- `wangsimni.yaml`: 왕십리점 수기 매출 기록.
- `mapo.yaml`: 마포점 수기 매출 기록.
- `wolgye.yaml`: 월계점 수기 매출 기록.
- `namseon/`: 남선매출 Google Drive 자료를 검증하는 SQLite 작업 공간. 검증 후 Supabase에 동기화한다.
- 대영매출은 Google Drive의 월별 이미지 원본을 로컬 OCR로 검증한 뒤 Supabase의
  `daeyoung_sales_sources`와 `daeyoung_sales_rows`에 저장한다.

## 매출 질문 처리 규칙

매출 관련 질문을 받으면 먼저 이 폴더를 기준으로 판단한다.

1. Supabase를 남선매출의 공용 조회 DB로 사용한다. 전환 검증 기간에는 `namseon/namseon_sales.db`와 `scripts/namseon_sales.py` 결과도 함께 확인한다.
2. 사용자가 매출 동기화를 요청하면 `scripts/namseon_sync_now.sh`를 실행한다. 이 명령은 Drive 원본을 SQLite로 검증한 뒤 날짜별로 Supabase에 안전하게 교체 저장하고, 다시 읽어 행 수를 검증한다. 루트 원본은 해당 월 폴더로 옮기며 전환 기간에는 SQLite DB 백업도 Drive에 유지한다.
   새 파일이 없으면 전체 SQLite 장부를 다시 대조하므로 이전 Supabase 적재 실패도 같은 명령으로 복구된다.
3. 같은 날짜 파일은 하나만 사용한다. `scripts/namseon_drive_sync.py`가 Google Sheets 파일과 최신 수정 시간을 기준으로 선택한다.
4. 관리매장 매출에서 아래 상품명이 포함된 제품은 행사팀 매출로 분류한다. 워터비매출은 `총매출 - 행사팀매출`로 계산한다.
   - `통낙지볶음`
   - `갑오징어무침`
   - `데친문어`
   - `불맛주꾸미볶음`
5. `month-total`은 위 4개 기본 행사팀 품목을 항상 자동 분류한다. 행사팀 품목이 추가될 때만 `--exclude` 옵션으로 추가 키워드를 넘긴다.
6. 사용자가 "20% 더해진 금액"처럼 수수료 차감 전 금액을 물으면, 차감 후 금액을 `0.8`로 나눈 값을 기준으로 답한다.

## 자주 쓰는 명령

```bash
python3 scripts/namseon_sales.py month-total --store mapo --month 2026-05
python3 scripts/namseon_sales.py month-total --store mia --month 2026-05
python3 scripts/namseon_sales.py month-total --store wangsimni --month 2026-05
python3 scripts/namseon_sales.py month-total --store wangsimni --month 2026-05 --exclude 추가행사팀품목
scripts/namseon_sync_now.sh
```

`*.db`, `*.db-shm`, `*.db-wal` 파일은 로컬/Drive 작업 산출물이며 git에 올리지 않는다.

## Supabase 설정

- 스키마: `supabase/migrations/20260828120000_namseon_sales.sql`
- 적재 CLI: `scripts/namseon_supabase_sync.py`
- 필수 환경변수: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- 최초 이관: `python3 scripts/namseon_supabase_sync.py`
- 날짜별 재반영: `python3 scripts/namseon_supabase_sync.py --date 2026-08-28`

서비스 역할 키는 서버 환경변수로만 관리하며 저장소나 Drive 파일에 기록하지 않는다.

## 대영매출 설정

- 원본: Google Drive `대영매출` 폴더의 월별 이미지
- 스키마: `supabase/migrations/20260828150000_daeyoung_sales.sql`
- OCR CLI: `scripts/daeyoung_sales_ocr.py`
- 적재 CLI: `scripts/daeyoung_supabase_sync.py`
- 월계점은 매월 둘째·넷째 일요일 정기휴무로 판정한다.
- OCR 합계가 화면 하단 합계와 다르면 삭제하지 않고 `review_required`로 저장한다.
- 원본 파일 ID와 링크를 보존하며 같은 날짜 재처리는 날짜별로 원자 교체한다.
