"""Read-only queue and Linux supervisor preflight. No claims or scale commands."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import urllib.request
import urllib.error

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    request = urllib.request.Request(
        os.environ['SUPABASE_URL'].rstrip('/') + '/rest/v1/rpc/get_scale_active_queue_health',
        data=b'{}', method='POST',
        headers={'apikey': os.environ['SUPABASE_SERVICE_ROLE_KEY'],
                 'Authorization': 'Bearer ' + os.environ['SUPABASE_SERVICE_ROLE_KEY'],
                 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        rows = json.load(response)
    if {row['queue_name'] for row in rows} != {'product_change', 'product_refresh', 'text_change', 'text_refresh'}:
        raise RuntimeError('queue_health_incomplete')
    queues = {row['queue_name']: row['processing_count'] for row in rows}
    spec = importlib.util.spec_from_file_location('cutover_v0', args.root / 'scale-data/tools/v0_scale_sync.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runtime = module.build_runtime(args.root, args.root / 'config/scale-product-change-sync.json',
                                   args.root / 'config/store-scale-sync.json')
    json.loads((args.root / 'config/cl5200-field-profile.json').read_text(encoding='utf-8'))
    indexes = {}
    for app, stream in runtime.change_stores.items():
        store_root = Path(stream['record_index_root']) / stream['controller_store_id']
        candidates = [p for p in store_root.iterdir() if p.is_dir() and not p.name.startswith('.')
                      and '.partial-' not in p.name and all((p / f).is_file() for f in ('plu.json', 'manifest.json', 'seacode-snapshot.json'))]
        latest = max(candidates, key=lambda p: p.stat().st_mtime_ns)
        records = json.loads((latest / 'plu.json').read_text(encoding='utf-8'))['records']
        for record in records:
            runtime.change.resolve_record_sequence(stream, record['plu'])
        indexes[app] = len(records)
    print(json.dumps({'processing': queues, 'registered_stores': sorted(runtime.refresh_stores),
                      'verified_target_indexes': indexes,
                      'circuit_open': module.circuit_marker_path(runtime).exists()}))
    return 2 if any(queues.values()) else 0

if __name__ == '__main__':
    raise SystemExit(main())
