# 대영매출 지침

월계점의 대영상사 매출 이미지 OCR, 검증과 조회 규칙을 정의한다.

## 데이터 흐름

```text
Google Drive 월별 매출 이미지
→ 로컬 OCR
→ 화면 합계 대조
→ Supabase 저장
→ 검증상태를 포함해 조회
```

## 기준 데이터

- 대상 매장: 월계점
- 원본: Google Drive `대영매출` 폴더의 월별 이미지
- OCR CLI: `scripts/daeyoung_sales_ocr.py`
- 적재 CLI: `scripts/daeyoung_supabase_sync.py`
- 스키마: `supabase/migrations/20260828150000_daeyoung_sales.sql`
- 원본 테이블: `daeyoung_sales_sources`
- 매출 행 테이블: `daeyoung_sales_rows`

## 검증 규칙

- OCR 결과를 화면 하단 합계와 대조한다.
- OCR 합계가 화면 합계와 다르면 자료를 삭제하거나 확정하지 않고 `review_required`로 저장한다.
- 검토 대기 자료를 확정 매출 합계에 포함할 때는 그 사실을 명시한다.
- 원본 파일 ID와 링크를 보존한다.
- 같은 날짜를 다시 처리하면 기존 날짜 자료를 원자적으로 교체한다.
- 적재 후 행 수와 합계를 다시 조회해 확인한다.

## 영업일 규칙

- 월계점은 매월 둘째·넷째 일요일을 정기휴무로 판정한다.
- 휴무일의 빈 매출은 누락과 구분한다.
- 이미지가 없거나 판독할 수 없는 날짜는 0원으로 임의 확정하지 않는다.
