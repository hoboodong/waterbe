"""Read-only app activity across phones; never submits or replays a job."""
import argparse
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

PROJECT = 'uvlmxspvgaagqaisdvhj'
STORES = {'mia', 'mapo', 'wolgye', 'wangsimni', 'mooner'}
FIELDS = 'id,store_id,operation_id,occurred_at,received_at,feature,stage,result,route,target,error_code'


def query(sql):
    cli = os.environ.get('WATERBE_SUPABASE_CLI') or shutil.which('supabase')
    if not cli:
        candidate = Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/SupabaseCLI/bin/supabase.exe'
        if candidate.is_file(): cli = str(candidate)
    if not cli: raise RuntimeError('configured_cli_required')
    result = subprocess.run([cli, 'db', 'query', '--linked', '--project-ref', PROJECT,
        sql, '-o', 'json'], capture_output=True, encoding='utf-8', timeout=30, check=True)
    return json.loads(result.stdout)['rows']


def read(store, date, feature=None, operation_id=None, limit=500, execute=query):
    if store not in STORES or not 1 <= limit <= 5000:
        raise ValueError('invalid_store_or_limit')
    if feature and not re.fullmatch(r'[a-z_]{1,40}', feature):
        raise ValueError('invalid_feature')
    start = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=timezone(timedelta(hours=9)))
    checked = datetime.now(timezone.utc)
    where = [f"store_id='{store}'", f"occurred_at>='{start.isoformat()}'",
        f"occurred_at<'{(start+timedelta(days=1)).isoformat()}'", f"received_at<='{checked.isoformat()}'"]
    if feature: where.append(f"feature='{feature}'")
    if operation_id: where.append(f"operation_id='{uuid.UUID(operation_id)}'")
    rows = []
    while len(rows) <= limit:
        size = min(100, limit + 1 - len(rows))
        page = execute(f"SELECT {FIELDS} FROM public.operation_diagnostics WHERE " +
            ' AND '.join(where) + f' ORDER BY received_at,id LIMIT {size} OFFSET {len(rows)}')
        rows.extend(page)
        if len(page) < size or len(rows) > limit: break
    return {'status': 'partial' if len(rows) > limit else 'available',
        'store': store, 'business_date': date, 'checked_at': checked.isoformat(),
        'events': rows[:limit], 'source': 'operation_diagnostics',
        'warnings': ['Only received instrumented events; offline/uninstrumented phones are invisible.',
            'Local/transport return is not physical or cloud verification.',
            'No commands, retries or work-state changes are performed.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True, choices=sorted(STORES))
    parser.add_argument('--date', required=True)
    parser.add_argument('--feature')
    parser.add_argument('--operation-id')
    parser.add_argument('--limit', type=int, default=500)
    args = parser.parse_args()
    try:
        result = read(args.store, args.date, args.feature, args.operation_id, args.limit)
    except Exception:
        result = {'status': 'unavailable', 'reason': 'activity_read_failed',
            'warning': 'Read failure is not absence of activity.'}
    print(json.dumps(result, ensure_ascii=True))
