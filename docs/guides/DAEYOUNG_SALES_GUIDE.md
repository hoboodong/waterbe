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

### 월계점 월매출 조회 — 먼저 실행

씽크패드 Waterbe/Telegram/Codex 세션에서는 다음 인증 포함 공식 입구로 조회한다.
일반 셸에 인증 환경변수가 없다는 이유로 DB 조회 불가라고 답하지 않는다.

```bash
~/.local/bin/waterbe-central daeyoung-month --month 2026-09
```

Windows에서는 `scripts/thinkpad.ps1 run -Command`로 같은 명령을 호출하거나,
인증이 준비된 현재 호스트에서 `python scripts/daeyoung_monthly_read.py --month 2026-09`를 쓴다.
이 조회는 GET만 수행한다. EM월계점과 SFM월계점은 같은 월계점으로 합산한다.
`total_sales`는 검토분 포함, `verified_sales`는 검증 완료분이다.
`review_dates`, `missing_dates`, `failed_dates`, `latest_imported_at`를 함께 확인한다.
실패 날짜가 있으면 전체 월매출로 확정하지 않는다. 누락 날짜는 0원으로 만들지 않는다.
DB에 적재된 자료가 있으면 Drive 월폴더 검색만으로 원본 없음이라고 답하지 않는다.
Drive 루트에도 날짜가 이미지 안에 표시된 숫자 이름 자료가 있을 수 있다.
조회 요청에서 OCR·동기화를 반복하지 않고, 실제 미확인 날짜만 별도 원본 대조한다.

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
