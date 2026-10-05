"""Observe central process/timer health; reuse durable history notifications."""
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import sys

root = Path.home()
sys.path.insert(0, str(root / '.local/lib/waterbe-history'))
import history_worker

CONTINUOUS = {'central_history': 'waterbe-history.service',
              'central_reads': 'caspi-remote-read.service',
              'central_supervisor': 'cas-supervisor.service'}
TIMED = {'central_aggregate': ('cas-aggregate-sync', {0, 1}),
         'central_receipts': ('caspi-receipt-sync', {0}),
         'central_reporter': ('cas-telegram-reporter', {0}),
         'central_backup': ('waterbe-central-backup', {0})}
TIMED['central_source_sync'] = ('waterbe-repo-sync', {0})

def properties(unit):
    result = subprocess.run(['systemctl', '--user', 'show', unit, '-p', 'LoadState',
                             '-p', 'ActiveState', '-p', 'ExecMainStatus'],
                            capture_output=True, text=True, timeout=10, check=True)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

def main():
    now = datetime.now(timezone.utc).isoformat(timespec='microseconds')
    states = {}
    for source, unit in CONTINUOUS.items():
        value = properties(unit)
        states[source] = value.get('LoadState') == 'loaded' and value.get('ActiveState') == 'active'
    for source, (name, allowed_codes) in TIMED.items():
        timer = properties(name + '.timer')
        service = properties(name + '.service')
        states[source] = timer.get('ActiveState') == 'active' and int(service.get('ExecMainStatus', '-1')) in allowed_codes
    database = root / '.local/state/waterbe-history/operations.db'
    for source, good in states.items():
        history_worker.health_notice(database, source, good, now)
    history_worker.publish_notices(database, root / '.local/state/waterbe-central/logs')
    print(json.dumps({'checked_at': now, 'process_health': states, 'physical_scale_verified': False}))
    return 0 if all(states.values()) else 1

if __name__ == '__main__':
    raise SystemExit(main())
