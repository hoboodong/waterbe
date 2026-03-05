# 워터비 작업 로그

## 2026-03-03

### 완료한 작업
- `/home/sdg/waterbe/` 폴더 생성
- `waterbe.md` 파일 생성 및 사업 기본 정보 정리
  - 사업 개요 (사업자명, 업종, 운영 방식)
  - 매장 현황 (왕십리점, 마포점, 월계점)
- 왕십리점 제품 라인업 입력
  - 밀키트 12종 (제품명 / 단위 / 가격 포함)
  - 단품 상품 11종 (제품명 / 단위 / 가격 포함, 국산흑골뱅이 가격 미기입)
  - 게장류 3종 (제품명 / 단위 / 가격 포함)
- 마포점 / 월계점 제품 라인업 폼 생성 (내용 미입력 상태)

### 다음 작업 (TODO)
- [ ] 마포점 제품 라인업 입력
- [ ] 월계점 제품 라인업 입력
- [ ] 국산흑골뱅이 가격 확인 후 입력 (왕십리점)
- [ ] 운영 구조 섹션 채우기 (직원 현황, 매입처/공급망, 수수료율, 매출 현황)
- [ ] 과제 / 메모 섹션 구체화

### 파일 구조
```
/home/sdg/waterbe/
├── waterbe.md    # 사업 전체 정보 정리 문서
└── WORKLOG.md    # 작업 로그 (이 파일)
```

---

## 2026-03-05

### 완료한 작업
- 온톨로지 데이터 관리 에이전트 설계 및 구현
  - `ontology/schema.yaml` 작성 (v1.1)
    - 클래스 정의: Store, Product, Category, Ingredient, Recipe
    - 관계 정의: carries, belongsTo, soldAt, subClassOf, forProduct, atStore, uses
    - 제약조건 및 nullable 규칙 포함
  - `ontology/instances/stores.yaml`: 왕십리·마포·월계점 3개 매장
  - `ontology/instances/categories.yaml`: 수산물·밀키트·단품·게장류 4개 카테고리
  - `ontology/instances/products.yaml`: 왕십리점 전체 26개 상품 이전 (밀키트 12, 단품 11, 게장류 3)
  - `ontology/instances/ingredients.yaml`: 수산물·채소·양념·육수 26개 재료
  - `ontology/instances/recipes.yaml`: 문어전복해물탕 왕십리점 레시피 1개 (예시)
  - `ontology/AGENT.md`: 에이전트 역할·CRUD 규칙·ID 명명 규칙 문서
- `waterbe.md` 표 서식 정리
  - 왕십리점 단품/게장류 헤더 열 수 불일치 수정
  - 가격 쉼표 서식 통일 (예: 23800 → 23,800)

### 다음 작업 (TODO)
- [ ] 마포점 제품 라인업 입력
- [ ] 월계점 제품 라인업 입력
- [ ] 국산흑골뱅이 가격 확인 후 입력 (왕십리점 `prod_sp_007`)
- [ ] 왕십리점 나머지 밀키트 레시피 입력 (현재 1개만 입력됨)
- [ ] 마포점·월계점 레시피 입력
- [ ] 운영 구조 섹션 채우기 (직원 현황, 매입처/공급망, 수수료율, 매출 현황)

### 파일 구조
```
/home/sdg/waterbe/
├── waterbe.md              # 사업 전체 정보 정리 문서
├── WORKLOG.md              # 작업 로그 (이 파일)
└── ontology/
    ├── schema.yaml         # 온톨로지 스키마 (클래스·속성·관계)
    ├── AGENT.md            # 에이전트 역할·규칙 문서
    └── instances/
        ├── stores.yaml
        ├── categories.yaml
        ├── products.yaml
        ├── ingredients.yaml
        └── recipes.yaml
```
