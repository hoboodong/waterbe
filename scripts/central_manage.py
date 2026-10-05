"""Bounded central operations for the local ThinkPad operator. No business writes."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid

import history_worker
import operation_history as history

COMPONENTS = {
    'history': 'waterbe-history.service',
    'read': 'caspi-remote-read.service',
    'supervisor': 'cas-supervisor.service',
    'aggregate': 'cas-aggregate-sync.timer',
    'receipts': 'caspi-receipt-sync.timer',
    'reporter': 'cas-telegram-reporter.timer',
    'health': 'waterbe-central-health.timer',
    'backup': 'waterbe-central-backup.timer',
}


def run(args, timeout=30):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def inspect(component):
    unit = COMPONENTS[component]
    result = run(['systemctl', '--user', 'show', unit, '-p', 'Id', '-p', 'ActiveState',
                  '-p', 'SubState', '-p', 'ExecMainStatus', '-p', 'UnitFileState',
                  '-p', 'LastTriggerUSec', '-p', 'ActiveEnterTimestamp'])
    if result.returncode:
        raise RuntimeError('unit_status_unavailable')
    data = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if data.get('Id') != unit:
        raise RuntimeError('unit_status_incomplete')
    if unit.endswith('.timer'):
        last = run(['systemctl', '--user', 'show', unit.replace('.timer', '.service'),
                    '-p', 'ExecMainStatus', '-p', 'ActiveState', '-p', 'ExecMainExitTimestamp'])
        if last.returncode:
            raise RuntimeError('oneshot_status_unavailable')
        data['last_run'] = dict(line.split('=', 1) for line in last.stdout.splitlines() if '=' in line)
    return data


def record(database, operation, component, kind, result, evidence=None):
    now = datetime.now(timezone.utc).isoformat()
    event = dict(source='waterbe', event_id=str(uuid.uuid4()), kind=kind, result=result,
                 feature='central.manage', target=component, observed_at=now,
                 operation_id=operation, route='thinkpad_local_cli', rule_version='central-manage-v1')
    if evidence:
        event['evidence_ids'] = [evidence]
    event = history.validate(event)
    encoded = history.canonical(event)
    history_worker.initialize(database)
    with closing(history.connect(database, write=True)) as db, db:
        cursor = db.execute('''INSERT INTO events(source,event_id,feature,target,kind,result,
            observed_at,received_at,content_hash,body) VALUES(?,?,?,?,?,?,?,?,?,?)''',
            (event['source'], event['event_id'], event['feature'], component, kind, result,
             now, now, hashlib.sha256(encoded.encode()).hexdigest(), encoded))
        db.execute('INSERT INTO delivery(sequence) VALUES(?)', (cursor.lastrowid,))


def restart(component, database, root):
    # A circuit marker is a business verification incident, not a process restart problem.
    if component == 'supervisor':
        check = run([os.sys.executable, str(root / 'scripts/central_cutover_check.py'),
                     '--root', str(Path.home() / '.local/lib/cas-supervisor-20261005')], timeout=60)
        if check.returncode:
            raise RuntimeError('supervisor_preflight_requires_review')
        proof = json.loads(check.stdout)
        if proof['circuit_open'] or any(proof['processing'].values()):
            raise RuntimeError('supervisor_business_state_requires_review')
    before = inspect(component)
    if before.get('UnitFileState') != 'enabled':
        raise RuntimeError('disabled_unit_requires_explicit_review')
    operation = 'central-restart-' + str(uuid.uuid4())
    record(database, operation, component, 'request', 'pending')
    try:
        command = run(['systemctl', '--user', 'restart', COMPONENTS[component]], timeout=330)
        after = inspect(component)
        good = command.returncode == 0 and after.get('ActiveState') == 'active'
        result = 'succeeded' if good else 'failed'
    except Exception:
        record(database, operation, component, 'result', 'uncertain')
        raise RuntimeError('restart_outcome_requires_status_check') from None
    evidence_body = {'operation_id': operation, 'component': component, 'before': before,
                     'after': after, 'result': result}
    evidence_root = database.parent / 'manager-evidence'
    evidence_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = evidence_root / (operation + '.json')
    staging = path.with_suffix('.partial')
    with staging.open('x', encoding='utf-8') as stream:
        json.dump(evidence_body, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    staging.chmod(0o600)
    staging.rename(path)
    record(database, operation, component, 'result', result,
           'central-manager:' + operation)
    return evidence_body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'restart'])
    parser.add_argument('component', nargs='?', choices=list(COMPONENTS))
    parser.add_argument('--approved', action='store_true', help='Explicit operator authorization, not authentication')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    database = Path.home() / '.local/state/waterbe-history/operations.db'
    try:
        if args.action == 'check':
            names = [args.component] if args.component else COMPONENTS
            data = {'checked_at': datetime.now(timezone.utc).isoformat(),
                    'components': {name: inspect(name) for name in names},
                    'physical_scale_verified': False}
        else:
            if not args.component or not args.approved:
                parser.error('restart requires one component and --approved')
            if not database.is_file():
                raise RuntimeError('central_history_missing')
            data = restart(args.component, database, root)
        print(json.dumps(data, ensure_ascii=False))
        return 0
    except Exception as error:
        # Never print subprocess stderr, environment, exception bodies or credentials.
        safe = str(error) if isinstance(error, RuntimeError) else 'management_check_failed'
        print(json.dumps({'status': 'requires_review', 'reason': safe}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
