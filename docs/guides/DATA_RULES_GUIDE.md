# 공통 데이터 작성·검증 지침

워터비 YAML 전반에 적용되는 작성, 이력, 무결성 규칙을 정의한다.

## YAML 구조

- 최상위 `instances:` 아래에 레코드를 둔다.
- 각 레코드는 `id`, `class`, `data`와 필요한 경우 `relations`를 가진다.
- 참조 전에 대상 ID와 이름을 원본 파일에서 확인한다.
- 날짜는 `YYYY-MM-DD` 형식을 사용한다.
- 한국어 업무명과 기존 주석을 보존한다.
- 작은 수정 때문에 큰 파일 전체를 재포맷하지 않는다.

## 이력 보존

- PriceHistory, Recipe, ProductionTemplate은 변경 시 새 레코드를 추가한다.
- ProductionPlan의 `dailyPlan`은 유지하고 조정은 `dailyAdjusted`에 기록한다.
- InventorySnapshot과 InboundRecord는 발생할 때마다 새 레코드를 추가한다.
- 명시적인 오류 정정 요청이 아니면 과거 업무기록을 덮어쓰지 않는다.

## 주요 무결성 조건

- SalesRecord의 `totalAmount`는 `qty × unitPrice`와 일치해야 한다.
- 같은 매장·상품에 현재 유효한 Recipe와 ProductionTemplate은 각각 최대 하나다.
- ProductionPlan의 상품·매장·주 시작일 조합은 유일하다.
- Staff의 `telegramId`는 유일하다.

## 변경 후 검증

```bash
python3 - <<'PY'
from pathlib import Path
import yaml

for path in sorted(Path('.').glob('**/*.yaml')):
    if '.git' in path.parts:
        continue
    with path.open(encoding='utf-8') as f:
        yaml.safe_load(f)
    print(path)
PY
```
