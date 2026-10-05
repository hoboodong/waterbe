"""CAS import orchestration with shared health evidence; no scale writes."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--history-root', type=Path, required=True)
    parser.add_argument('--history-db', type=Path, required=True)
    parser.add_argument('--logs', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.history_root))
    import history_worker
    import central_aggregate_sync
    config = central_aggregate_sync.load_config(args.config)
    result = central_aggregate_sync.run(config)
    central_aggregate_sync.append_log(Path(config['log_path']), result)
    now = datetime.now(timezone.utc).isoformat(timespec='microseconds')
    errors = result.get('store_errors', {})
    for store in config['stores']:
        history_worker.health_notice(args.history_db, 'aggregate_sync_'+store['id'],
                                    store['id'] not in errors, now)
    history_worker.publish_notices(args.history_db, args.logs)
    # A partial run remains visibly partial; systemd timer continues the next run.
    print('aggregate_import', result['status'], 'new_collections', result['imported_collections'],
          'unavailable_stores', ','.join(sorted(errors)), flush=True)
    return 1 if errors else 0

if __name__ == '__main__':
    raise SystemExit(main())
