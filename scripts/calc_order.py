#!/usr/bin/env python3
"""
발주량 자동 계산 스크립트
사용: python3 calc_order.py [store] [시작일YYYY-MM-DD] [일수]
기본: wolgye, 내일부터 7일

예) python3 calc_order.py
    python3 calc_order.py wolgye 2026-04-15 7
"""

import yaml, sys, re, math
from datetime import date, timedelta
from collections import defaultdict
from pathlib import Path

BASE  = Path.home() / '.openclaw/shared/waterbe'
INST  = BASE / 'instances'
MAST  = INST / 'master'

# ── 인수 파싱 ──────────────────────────────────────────────────
store_key = 'wolgye'
today     = date.today()
start     = today + timedelta(days=1)
days      = 7

args = sys.argv[1:]
for a in args:
    if re.match(r'\d{4}-\d{2}-\d{2}', a): start = date.fromisoformat(a)
    elif re.match(r'\d+$', a):             days  = int(a)
    else:                                  store_key = a

STORE = f'store_{store_key}'
end   = start + timedelta(days=days - 1)
date_range = [start + timedelta(days=i) for i in range(days)]
DOW = {0:'mon', 1:'tue', 2:'wed', 3:'thu', 4:'fri', 5:'sat', 6:'sun'}

# ── YAML 로드 헬퍼 ─────────────────────────────────────────────
def load_dict(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    return {i['id']: i for i in (data.get('instances') or [])}

def load_list(path):
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get('instances') or []

# ── 데이터 로드 ────────────────────────────────────────────────
pspecs    = load_dict(MAST / 'purchase_specs.yaml')
ings      = load_dict(MAST / 'ingredients.yaml')
recipes   = load_list(MAST / f'recipes/{store_key}.yaml')
templates = load_list(INST / f'production/templates/{store_key}.yaml')
inv_list  = load_list(INST / f'inventory/{store_key}.yaml')

# ── 활성 템플릿 ────────────────────────────────────────────────
def active_tmpl(prod_id, d):
    ds = str(d)
    cands = [t for t in templates
             if t['relations']['forProduct'] == prod_id
             and t['relations']['atStore'] == STORE
             and t['data']['effectiveFrom'] <= ds
             and (t['data']['effectiveTo'] is None or t['data']['effectiveTo'] >= ds)]
    return cands[-1] if cands else None

# ── 레시피 인덱스 ──────────────────────────────────────────────
recipe_by_prod = {}
for r in recipes:
    recipe_by_prod[r['relations']['forProduct']] = r

# ── 전체 생산량 계산 ───────────────────────────────────────────
prod_ids = list({t['relations']['forProduct'] for t in templates
                 if t['relations']['atStore'] == STORE})
prod_qty = defaultdict(float)
for pid in prod_ids:
    for d in date_range:
        t = active_tmpl(pid, d)
        if t:
            prod_qty[pid] += t['data']['dailyQty'].get(DOW[d.weekday()], 0)

# ── 재료별 순 필요량 계산 ──────────────────────────────────────
ing_net_g    = defaultdict(float)   # ingredient_id → net 그램
ing_net_pack = defaultdict(float)   # ingredient_id → net 팩수 (소스 등)
ing_pspec_id = {}                   # ingredient_id → 레시피 기준 pspec_id

for pid, total in prod_qty.items():
    recipe = recipe_by_prod.get(pid)
    if not recipe:
        continue
    for use in recipe['relations'].get('uses', []):
        iid    = use['ingredient']
        amount = use.get('amount') or 0
        unit   = use.get('unit', 'g')
        psid   = use.get('pspec')
        if psid:
            ing_pspec_id[iid] = psid

        if unit == 'g':
            ing_net_g[iid] += amount * total
        elif unit == 'kg':
            ing_net_g[iid] += amount * 1000 * total
        elif unit == '마리':
            # countPerKg으로 g 환산 (예: 30/40 → 35마리/kg → 1마리≈28.6g)
            ps_data = pspecs.get(psid, {}).get('data', {}) if psid else {}
            cpk = ps_data.get('countPerKg') or 35
            ing_net_g[iid] += (amount / cpk * 1000) * total
        elif unit == '팩':
            ing_net_pack[iid] += amount * total
        # 후레시, 롤 등 무시

# ── 손실률 적용 → 실 필요량(g) ────────────────────────────────
ing_gross_g = {}
for iid, net in ing_net_g.items():
    d = ings.get(iid, {}).get('data', {})
    thaw = d.get('thawLossRate', 0) or 0
    trim = d.get('trimLossRate', 0) or 0
    yr   = (1 - thaw / 100) * (1 - trim / 100)
    ing_gross_g[iid] = net / yr if yr > 0 else net

# ── 최신 재고 스냅샷 ──────────────────────────────────────────
def latest_snap(iid):
    snaps = [s for s in inv_list
             if s['relations']['forIngredient'] == iid
             and s['relations']['atStore'] == STORE]
    return sorted(snaps, key=lambda x: x['data']['date'])[-1] if snaps else None

def snap_kg(snap, recipe_psid=None):
    """재고 스냅샷 → kg 환산"""
    if not snap:
        return 0.0
    sd   = snap['data']
    qty  = float(sd.get('quantity') or 0)
    unit = sd.get('unit', '개')

    if unit == 'kg':
        return qty

    # unit == '개' (팩/마리/조각 등)
    # 재고에 기록된 pspec 우선, 없으면 레시피 pspec
    psid = snap['relations'].get('forPurchaseSpec') or recipe_psid
    ps   = pspecs.get(psid, {}).get('data', {}) if psid else {}

    ppb = ps.get('packCount')      # 박스당 팩/마리/조각 수
    if ppb:
        m = re.search(r'([\d.]+)\s*kg', str(ps.get('orderUnit', '')))
        if m:
            return qty * float(m.group(1)) / ppb

    return qty  # 최후 수단: 그냥 수량 반환

def snap_pack(snap):
    if not snap:
        return 0.0
    return float(snap['data'].get('quantity') or 0)

# ── 발주 박스 수 계산 ──────────────────────────────────────────
def calc_order(short_kg, psid):
    """부족량 → 발주 박스수, 박스당 kg"""
    ps = pspecs.get(psid, {}).get('data', {}) if psid else {}
    ou = str(ps.get('orderUnit', ''))
    # kg 단위
    m = re.search(r'([\d.]+)\s*kg', ou)
    if m:
        unit_kg = float(m.group(1))
        boxes   = math.ceil(short_kg / unit_kg)
        return boxes, unit_kg
    # g 단위 (예: 500g)
    m = re.search(r'([\d.]+)\s*g\b', ou)
    if m:
        unit_kg = float(m.group(1)) / 1000
        boxes   = math.ceil(short_kg / unit_kg)
        return boxes, unit_kg
    return None, None

def ing_name(iid):
    return ings.get(iid, {}).get('data', {}).get('name', iid)

def prod_name(pid):
    r = recipe_by_prod.get(pid, {})
    return r.get('data', {}).get('name', pid) if r else pid

# ── 출력 ──────────────────────────────────────────────────────
SEP = '─' * 80

print(f'\n{"="*80}')
print(f'  월계점 발주 계산  {start} ~ {end}  ({days}일)')
print(f'{"="*80}\n')

# 생산량 요약
print('[ 기간 생산량 ]')
for pid, qty in sorted(prod_qty.items()):
    print(f'  {prod_name(pid)}: {int(qty)}개')

# ── kg 단위 품목 발주 ──────────────────────────────────────────
print(f'\n[ 발주 필요 — 수산물·육류 ]\n')
print(f"  {'재료':<22} {'순필요':>8} {'실필요':>8} {'재고':>8} {'부족':>8}  발주량")
print(f'  {SEP}')

ok_list  = []
warn_list = []

MIN_KG = 0.05  # 50g 미만 무시

for iid, gross_g in sorted(ing_gross_g.items(), key=lambda x: -x[1]):
    gross_kg = gross_g / 1000
    net_kg   = ing_net_g[iid] / 1000
    psid     = ing_pspec_id.get(iid)
    snap     = latest_snap(iid)
    inv_kg   = snap_kg(snap, psid)
    short    = max(0.0, gross_kg - inv_kg)
    name     = ing_name(iid)

    if short <= 0 or gross_kg < MIN_KG:
        if gross_kg >= MIN_KG:
            ok_list.append((name, inv_kg, gross_kg))
        continue

    boxes, unit_kg = calc_order(short, psid)
    if boxes and unit_kg:
        order_str = f'{boxes}박스 ({boxes * unit_kg:.1f}kg)'
    else:
        ps_ou = pspecs.get(psid, {}).get('data', {}).get('orderUnit', '?') if psid else '?'
        order_str = f'확인필요 ({ps_ou})'
        warn_list.append((name, short, ps_ou))

    print(f'  {name:<22} {net_kg:>7.1f}kg {gross_kg:>7.1f}kg {inv_kg:>7.1f}kg {short:>7.1f}kg  {order_str}')

# ── 팩 단위 품목 발주 (소스류) ────────────────────────────────
if ing_net_pack:
    print(f'\n[ 발주 필요 — 소스·팩 단위 ]\n')
    print(f"  {'재료':<22} {'순필요':>8} {'재고':>8} {'부족':>8}  발주량")
    print(f'  {SEP}')

    for iid, net_pack in sorted(ing_net_pack.items(), key=lambda x: -x[1]):
        psid  = ing_pspec_id.get(iid)
        snap  = latest_snap(iid)
        inv   = snap_pack(snap)
        short = max(0.0, net_pack - inv)
        name  = ing_name(iid)

        if short <= 0:
            ok_list.append((name, inv, net_pack))
            continue

        ps    = pspecs.get(psid, {}).get('data', {}) if psid else {}
        pc    = ps.get('packCount')
        ou    = str(ps.get('orderUnit', '?'))
        if pc and pc > 1:
            boxes     = math.ceil(short / pc)
            order_str = f'{boxes}박스 ({boxes * pc}팩)'
        elif '팩' in ou or (pc and pc == 1):
            # 1팩씩 발주하는 품목
            order_str = f'{int(math.ceil(short))}팩'
        else:
            order_str = f'확인필요 ({ou})'

        print(f'  {name:<22} {net_pack:>7.0f}팩 {inv:>7.0f}팩 {short:>7.0f}팩  {order_str}')

# ── 충분한 품목 ────────────────────────────────────────────────
print(f'\n[ 충분 — 발주불필요 ]')
for name, inv, need in sorted(ok_list, key=lambda x: x[0]):
    unit = 'kg' if isinstance(need, float) else '팩'
    print(f'  ✓ {name}: 재고 {inv:.1f} / 필요 {need:.1f}')

# ── 경고 ──────────────────────────────────────────────────────
if warn_list:
    print(f'\n[ ⚠ 발주단위 확인 필요 ]')
    for name, short, ou in warn_list:
        print(f'  ! {name}: {short:.1f}kg 부족, 발주단위={ou}')

print()
