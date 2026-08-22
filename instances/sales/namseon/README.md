# 남선매출 통합 DB

남선매출 Google Drive 일별 스프레드시트를 SQLite로 누적해서 빠르게 조회하기 위한 작업 공간이다.

매출 질문을 처리할 때는 먼저 상위 문서 `instances/sales/README.md`의 공통 규칙을 따른다.

## 파일

- `namseon_sales.db`: 생성되는 SQLite DB. git에는 포함하지 않는다.
- `scripts/namseon_sales.py`: DB 초기화, CSV import, 월 매출 조회 CLI.
- `scripts/namseon_drive_sync.py`: Google Drive `남선매출` 폴더 전체 동기화 CLI.

## 기본 사용

```bash
python3 scripts/namseon_sales.py init-db
```

Google Sheets 일별 파일을 CSV로 내보낸 뒤 import:

```bash
python3 scripts/namseon_sales.py import-csv /path/to/sales.csv \
  --date 2026-05-31 \
  --source-file-id 1-bix-maMyX89IsryrBDYPaquSdPpX3dMXVL9t_RakBE \
  --source-file-name "이마트매장 05월31일 매출현황"
```

월 매출 조회:

```bash
python3 scripts/namseon_sales.py month-total --store mapo --month 2026-05
python3 scripts/namseon_sales.py month-total --store mia --month 2026-05
python3 scripts/namseon_sales.py month-total --store wangsimni --month 2026-05
python3 scripts/namseon_sales.py month-total --store wangsimni --month 2026-05 \
  --exclude 추가행사팀품목
```

월 매출은 해당 월에 import된 가장 늦은 `sale_date` 파일의 `월누계금액`을 기준으로 계산한다. `통낙지볶음`, `갑오징어무침`, `데친문어`, `불맛주꾸미볶음`이 상품명에 포함되면 기본 행사팀 매출로 자동 분류하고, 워터비매출은 `총매출 - 행사팀매출`로 계산한다. `--exclude`는 기본 4개 품목 외에 추가 행사팀 품목이 있을 때만 사용한다.

## Google Drive 전체 동기화

```bash
python3 scripts/namseon_drive_sync.py --trash-duplicates
```

기본 Drive 폴더는 `남선매출`이다. 월별 하위 폴더와 루트 파일을 훑어서 파일명에서 날짜를 읽고, 같은 날짜 파일이 여러 개 있으면 Google Sheets 파일과 최신 수정 시간을 우선해서 하나만 DB에 넣는다. `--trash-duplicates`를 붙이면 선택되지 않은 중복 파일은 Drive 휴지통으로 보낸다.

일부 2026년 1월 이후 파일은 매장명 대신 점포코드 형식이다. 이 경우 `sales_rows.store`에는 `STORE_CODE:<점포코드>` 형식으로 저장된다.

## 새 파일만 빠르게 동기화

```bash
scripts/namseon_sync_now.sh
```

요청용 스크립트는 로컬 DB에 들어있는 마지막 `sale_date`의 다음날부터만 가져온다. Google Drive 최상위 루트와 남선매출 폴더를 함께 확인하고, 루트에 올라온 매출 원본 파일은 import 후 해당 월 폴더로 옮긴다. 동기화가 끝나면 Google Drive에 올려둔 `namseon_sales.db` 파일을 새 DB로 교체한다.

수동으로 시작 날짜를 지정하려면:

```bash
python3 scripts/namseon_drive_sync.py --from-date 2026-06-04 --include-drive-root --organize-root-files --trash-duplicates --upload-db
```

## 요청 시 동기화

사용자가 "매출 반영해줘", "남선매출 동기화해줘", "Drive에 올라온 매출파일 반영해줘"처럼 요청하면 아래 스크립트를 실행한다.

```bash
/home/sdg/waterbe/scripts/namseon_sync_now.sh
```

실행 내용은 아래와 같다.

```bash
python3 scripts/namseon_drive_sync.py --incremental --include-drive-root --organize-root-files --trash-duplicates --upload-db
```

실행 후 확인:

```bash
python3 scripts/namseon_drive_sync.py --incremental --include-drive-root --organize-root-files --dry-run
```
