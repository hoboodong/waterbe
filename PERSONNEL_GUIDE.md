# 워터비(WATERBE) 인사관리 가이드

> **에이전트에게**: 이 파일 하나만 읽으면 워터비 인사 데이터를 즉시 사용할 수 있습니다.

---

## 워터비란?
이마트 수산물 코너에 입점한 밀키트·단품 판매 사업. 현재 3개 매장 운영.
- **왕십리점** (store_wangsimni)
- **마포점** (store_mapo)
- **월계점** (store_wolgye)

---

## 관리 파일

| 파일 | 내용 |
|------|------|
| `instances/staff.yaml` | 직원 정보 (이름·텔레그램ID·역할·소속매장) |
| `instances/schedules.yaml` | 근무·기타 일정 |

---

## 클래스별 핵심 필드

### Staff (직원)
| 필드 | 설명 |
|------|------|
| name | 이름 |
| telegramId | 텔레그램 사용자 ID (숫자 문자열, 유일) |
| role | 팀장 / 직원 |
| atStore | 소속 매장 ID (직원만, 팀장은 null) |

### Schedule (일정)
| 필드 | 설명 |
|------|------|
| date | 일자 (YYYY-MM-DD) |
| endDate | 종료일 (하루짜리면 null) |
| type | 근무 / 기타 |
| title | 제목 |
| description | 상세 내용 (nullable) |
| assignee | 담당자 이름 (nullable) |
| createdBy | 등록한 팀장 이름 |
| atStore | 해당 매장 ID |

> **발주·생산 일정은 이 가이드 범위 밖.**
> 발주 → `InboundRecord`, 생산 → `ProductionPlan` (WATERBE_GUIDE.md 참조)

---

## 권한 규칙

```
메시지를 보낸 사람의 텔레그램 ID → staff.yaml에서 조회

팀장 (role: 팀장):
  - 전체 매장 일정·직원 조회 가능
  - 일정 등록·수정·삭제 가능
  - 직원 등록·수정 가능

직원 (role: 직원):
  - 자신의 소속 매장(atStore) 일정만 조회 가능
  - 일정·직원 등록·수정·삭제 불가

미등록 사용자:
  - "등록된 직원이 아닙니다. 팀장님께 등록을 요청해주세요." 안내
```

---

## 사용 예시

### 예시 1: 발신자 권한 확인 (모든 요청의 첫 단계)

```
Step 1. staff.yaml → 발신자 telegramId로 role·atStore 확인
Step 2. 권한에 따라 분기
        - 팀장: 모든 기능 허용
        - 직원: 조회만 허용 (본인 매장 한정)
        - 미등록: 안내 메시지 후 종료
```

### 예시 2: 일정 조회

```
Step 1. 발신자 권한 확인 (예시 1)
Step 2. schedules.yaml 읽기
        - 직원: atStore가 본인 매장인 항목만 필터
        - 팀장: 전체 항목
Step 3. 날짜 범위로 필터 (오늘 / 이번주 / 이번달 등)
Step 4. 매장별·날짜순으로 정리해서 출력
```

### 예시 3: 일정 등록 (팀장 전용)

```
Step 1. 발신자가 팀장인지 확인
Step 2. 대상 매장, 날짜, 종류(근무/기타), 제목, 담당자 확인
Step 3. schedules.yaml에 새 레코드 추가
        id: sched_{마지막 번호 + 1}
        createdBy: 팀장 이름
Step 4. 등록 완료 안내
```

### 예시 4: 일정 수정 (팀장 전용)

```
Step 1. 발신자가 팀장인지 확인
Step 2. 수정할 일정 확인 (날짜·제목으로 검색)
Step 3. schedules.yaml 해당 레코드 수정
Step 4. 수정 완료 안내
```

### 예시 5: 직원 등록 (팀장 전용)

```
Step 1. 발신자가 팀장인지 확인
Step 2. 이름, 텔레그램 ID, 역할, 소속 매장 확인
        - telegramId 중복 여부 먼저 확인
        - 직원이면 atStore 필수 / 팀장이면 atStore: null
Step 3. staff.yaml에 새 레코드 추가
        id: staff_{마지막 번호 + 1}
Step 4. 등록 완료 안내
```

### 예시 6: 직원 목록 조회 (팀장 전용)

```
Step 1. 발신자가 팀장인지 확인
Step 2. staff.yaml 전체 조회
Step 3. 매장별로 묶어서 출력
        출력 형식: 이름 | 역할 | 소속매장
```

---

## ID 명명 규칙

| 클래스 | 형식 | 예시 |
|--------|------|------|
| Staff | `staff_{순번}` | `staff_001` |
| Schedule | `sched_{순번}` | `sched_001` |

---

## 제약 사항

- `Staff.telegramId`는 유일해야 한다 (중복 등록 불가)
- `Staff.role`은 팀장 / 직원 중 하나
- `Staff.atStore`는 role이 직원일 때 필수, 팀장일 때 null
- `Schedule.type`은 근무 / 기타 중 하나
- `Schedule.date`는 YYYY-MM-DD 형식
- `Schedule.endDate`는 date 이후여야 한다
