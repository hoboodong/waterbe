# 남선매출 지침

왕십리점, 마포점, 미아점의 남선매출 원본 동기화, 검증과 조회 규칙을 정의한다.

## 데이터 흐름

```text
Google Drive 일별 스프레드시트
→ SQLite 검증
→ Supabase 날짜별 교체 저장
→ 행 수와 합계 재검증
→ 매출 조회
```

## 기준 데이터

- 공용 조회 DB: Supabase
- 전환 검증용 DB: `instances/sales/namseon/namseon_sales.db`
- 조회 CLI: `scripts/namseon_sales.py`
- Drive 동기화: `scripts/namseon_drive_sync.py`
- Supabase 적재: `scripts/namseon_supabase_sync.py`
- 요청용 통합 실행: `scripts/namseon_sync_now.sh`

`*.db`, `*.db-shm`, `*.db-wal`은 로컬·Drive 작업 산출물이며 Git에 올리지 않는다.

## 조회 규칙

- 월 매출은 해당 월에 가져온 가장 늦은 `sale_date` 파일의 `월누계금액`을 기준으로 계산한다.
- 전환 검증 기간에는 Supabase 결과와 SQLite CLI 결과를 함께 확인한다.
- 일부 자료가 매장명 대신 점포코드를 사용하면 `STORE_CODE:<점포코드>` 형태로 저장된다.

## 행사팀 매출

다음 상품명이 포함된 제품은 기본 행사팀 매출로 분류한다.

- `통낙지볶음`
- `갑오징어무침`
- `데친문어`
- `불맛주꾸미볶음`

```text
워터비 매출 = 총매출 - 행사팀 매출
```

`month-total`은 위 네 품목을 자동 분류한다. 추가 행사팀 품목이 있을 때만 `--exclude`로 키워드를 추가한다.

## 중복과 동기화

- 같은 날짜 파일은 하나만 사용한다.
- Google Sheets 형식과 최신 수정시각을 기준으로 선택한다.
- 루트와 `남선매출` 폴더를 함께 확인한다.
- 선택되지 않은 중복 파일은 사용자가 동기화를 요청한 흐름에서만 휴지통 처리한다.
- 루트 원본은 검증 후 해당 월 폴더로 정리한다.
- 새 파일이 없어도 전체 SQLite 장부와 Supabase를 대조해 이전 적재 실패를 복구한다.

사용자가 새 Drive 파일 반영이나 남선매출 동기화를 요청하면 실행한다.

```bash
scripts/namseon_sync_now.sh
```

실행 후 dry-run으로 새 변경이 남지 않았는지 확인한다.

```bash
python3 scripts/namseon_drive_sync.py --incremental --include-drive-root --organize-root-files --dry-run
```

## 자주 쓰는 조회

```bash
python3 scripts/namseon_sales.py month-total --store wangsimni --month 2026-05
python3 scripts/namseon_sales.py month-total --store mapo --month 2026-05
python3 scripts/namseon_sales.py month-total --store mia --month 2026-05
python3 scripts/namseon_sales.py month-total --store wangsimni --month 2026-05 --exclude 추가행사팀품목
```

## Supabase 설정

- 스키마: `supabase/migrations/20260828120000_namseon_sales.sql`
- 필수 환경변수: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- 최초 이관: `python3 scripts/namseon_supabase_sync.py`
- 날짜별 재반영: `python3 scripts/namseon_supabase_sync.py --date YYYY-MM-DD`
- 서비스 역할 키는 환경변수로만 관리하고 저장소나 Drive에 기록하지 않는다.
