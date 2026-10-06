"""Install approved health-notification-only release on the ThinkPad.

No scale commands, source credentials, outbox rewrites or business queue changes.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import uuid


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=90)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage',type=Path,required=True)
    parser.add_argument('--approved',action='store_true',required=True)
    args = parser.parse_args()
    home = Path.home()
    stage = args.stage.resolve()
    state = home / '.local/state/waterbe-central'
    if stage.parent != state or not stage.name.startswith('alert-policy-stage-'):
        raise ValueError('Unexpected staging directory')
    manifest = json.loads((stage/'manifest.json').read_text())
    for name,digest in manifest.items():
        if Path(name).name != name or hashlib.sha256((stage/name).read_bytes()).hexdigest() != digest:
            raise ValueError('Release hash mismatch')
    release = home / '.local/lib/waterbe-health-alert-v2-20261006'
    if release.exists():
        raise ValueError('Release already exists; inspect before retrying')
    operation = 'health-policy-' + str(uuid.uuid4())
    backup = state / operation
    backup.mkdir(mode=0o700)
    units = home / '.config/systemd/user'
    timers = ['waterbe-central-health.timer','cas-telegram-reporter.timer','cas-aggregate-sync.timer']
    for timer in timers:
        if command('systemctl','--user','is-active',timer).stdout.strip() != 'active':
            raise ValueError('Expected enabled timer is not active')
    replacements = {
        'waterbe-history.service': '/usr/bin/python3 '+str(release/'history_worker.py')+
            ' --database %h/.local/state/waterbe-history/operations.db --source-root %h/waterbe'
            ' --notification-root %h/.local/state/waterbe-central/logs watch',
        'waterbe-central-health.service': '/usr/bin/python3 '+str(release/'central_health_check.py'),
        'cas-telegram-reporter.service': '/usr/bin/flock -n %h/.local/state/waterbe-central/telegram-failure-reporter/reporter.lock'
            ' /usr/bin/python3 '+str(release/'telegram_failure_reporter.py')+
            ' --config %h/.local/state/waterbe-central/telegram-failure-reporter/config.json'
            ' --runtime-root %h/.local/state/waterbe-central/telegram-failure-reporter once',
        'cas-aggregate-sync.service': '/usr/bin/python3 %h/.local/lib/cas-central-adaptive-20261006/central_aggregate_runner.py'
            ' --config %h/.local/state/cas-central/aggregate-config.json --history-root '+str(release)+
            ' --history-db %h/.local/state/waterbe-history/operations.db --logs %h/.local/state/waterbe-central/logs',
    }
    for unit in replacements:
        shutil.copy2(units/unit,backup/unit)
        override = units/(unit+'.d')/'health-policy-v2.conf'
        if override.exists():
            raise ValueError('Policy override already exists')
    command('systemctl','--user','stop',*timers)
    modified = []
    try:
        # These are read-only observers/importers/reporters, not scale writers.
        command('systemctl','--user','stop','waterbe-history.service',
                'waterbe-central-health.service','cas-telegram-reporter.service','cas-aggregate-sync.service')
        db_path = home/'.local/state/waterbe-history/operations.db'
        with closing(sqlite3.connect(db_path)) as source, closing(sqlite3.connect(backup/'operations.db')) as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup integrity failed')
        reporter = state/'telegram-failure-reporter'
        for name in ('operation-state.json','state.json','outbox.json'):
            shutil.copy2(reporter/name,backup/name)
        release.mkdir(mode=0o700)
        for name in manifest:
            shutil.copy2(stage/name,release/name)
        sys.path.insert(0,str(release))
        import history_worker as worker
        import operation_history as history
        worker.initialize(db_path)
        with closing(history.connect(db_path,write=True)) as db,db:
            # Create policy state without manufacturing any success observation.
            db.execute('''CREATE TABLE IF NOT EXISTS health_alerts (
                source TEXT PRIMARY KEY,bad_since TEXT,good_since TEXT,
                last_checked TEXT NOT NULL,last_notified TEXT,opened INTEGER NOT NULL)''')
        for unit,execution in replacements.items():
            folder = units/(unit+'.d')
            folder.mkdir(exist_ok=True)
            override = folder/'health-policy-v2.conf'
            override.write_text('[Service]\nExecStart=\nExecStart='+execution+'\n')
            modified.append(override)
        command('systemctl','--user','daemon-reload')
        command('systemctl','--user','start','waterbe-history.service',*timers)
        proof = {'operation_id':operation,'release':str(release),'hashes':manifest,
                 'backup':str(backup),'policy':'health-debounce-v2',
                 'delay_seconds':300,'reminder_seconds':1800,'recovery_seconds':300,
                 'business_writes':False,'outbox_preserved':True,
                 'checked_at':datetime.now(timezone.utc).isoformat()}
        evidence = db_path.parent/'manager-evidence'
        evidence.mkdir(exist_ok=True)
        (evidence/(operation+'.json')).write_text(json.dumps(proof,sort_keys=True))
        event = dict(event_id=operation,operation_id=operation,source='waterbe',
                     kind='result',result='succeeded',feature='central.alert_policy',
                     target='central_notifications',observed_at=proof['checked_at'],
                     evidence_ids=['central-policy:'+operation],rule_version='health-debounce-v2')
        history.append(db_path,event)
        with closing(history.connect(db_path,write=True)) as db,db:
            sequence = db.execute('SELECT sequence FROM events WHERE source=? AND event_id=?',
                                  ('waterbe',operation)).fetchone()[0]
            db.execute('INSERT OR IGNORE INTO delivery(sequence) VALUES(?)',(sequence,))
        print(json.dumps(proof))
    except Exception:
        for path in modified:
            # Only overrides created by this installation are removed on rollback.
            path.unlink()
        command('systemctl','--user','daemon-reload')
        command('systemctl','--user','start','waterbe-history.service',*timers)
        raise


if __name__ == '__main__':
    main()
