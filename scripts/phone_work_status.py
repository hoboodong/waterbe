"""Read shared work observations; never sends scale commands or repairs jobs."""
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def read(store):
    if store not in ('mia', 'mapo', 'wolgye', 'wangsimni', 'mooner'):
        raise ValueError('unregistered_store')
    base = os.environ.get('SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    query = urlencode({'select': 'operation_id,store_id,feature,target,observed_at,received_at,details,error_code',
        'store_id': 'eq.' + store, 'order': 'received_at.desc,operation_id.desc', 'limit': 500})
    try:
        if base.startswith('https://') and key:
            req = Request(base + '/rest/v1/scale_shared_work?' + query,
                headers={'apikey': key, 'Authorization': 'Bearer ' + key})
            rows = json.load(urlopen(req, timeout=20))
        else:
            from system_check import find_cli
            cli = find_cli()
            if not cli:
                raise ValueError('configured_read_route_required')
            sql = "SELECT operation_id,store_id,feature,target,observed_at,received_at,details,error_code FROM public.scale_shared_work WHERE store_id='" + store + "' ORDER BY received_at DESC,operation_id DESC LIMIT 500"
            run = subprocess.run([cli,'db','query','--linked','--project-ref',
                'uvlmxspvgaagqaisdvhj',sql,'-o','json'],capture_output=True,text=True,timeout=30,check=True)
            rows=json.loads(run.stdout)['rows']
    except Exception:
        return {'status': 'unavailable', 'reason': 'phone_observation_read_failed'}
    latest = {}
    for row in rows:
        latest.setdefault(row['operation_id'], row)
    now = datetime.now(timezone.utc)
    result = []
    for row in latest.values():
        details = row['details']
        if details['status'] == 'applied':
            continue
        observed = datetime.fromisoformat(row['observed_at'].replace('Z', '+00:00'))
        result.append({'operation_id': row['operation_id'], 'target': row.get('target'),
            'feature': row['feature'], 'result': details['status'],
            'observed_at': row['observed_at'], 'server_received_at': row['received_at'],
            'source': details.get('source', 'phone'),
            'freshness': 'stale' if (now-observed).total_seconds() > 1200 else 'recent',
            'error_code': row.get('error_code'), 'work_details': details})
    return {'status': 'partial' if len(rows) == 500 else 'available', 'store': store,
        'checked_at': now.isoformat(), 'work': result,
        'warnings': ['Last shared observations, not a live phone or scale read.',
            'Missing records do not prove no pending work.',
            'At most 500 recent events; older unresolved work may be outside this scope.',
            'work_details requires the new DB contract and installed app.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', required=True)
    args = parser.parse_args()
    print(json.dumps(read(args.store), ensure_ascii=False, indent=2))
