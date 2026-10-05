"""Online central state backup. Credentials are deliberately excluded."""
import argparse
from contextlib import ExitStack, closing
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path, default=Path.home())
    args = parser.parse_args()
    home = args.home.resolve()
    state = home / '.local/state'
    backups = state / 'waterbe-central/backups'
    backups.mkdir(parents=True, exist_ok=True, mode=0o700)
    with ExitStack() as stack:
        lock = stack.enter_context((backups / 'backup.lock').open('a'))
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        reporter_lock = stack.enter_context((state / 'waterbe-central/telegram-failure-reporter/reporter.lock').open('a'))
        fcntl.flock(reporter_lock, fcntl.LOCK_EX)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        target = backups / (stamp + '.partial')
        target.mkdir(mode=0o700)
        databases = {
            'history.db': state / 'waterbe-history/operations.db',
            'aggregate.sqlite3': state / 'cas-central/aggregate-central.sqlite3',
            'receipt.sqlite3': state / 'cas-central/receipt-state.sqlite3',
            'dispatch.sqlite3': state / 'cas-supervisor/operations/caspi-remote-dispatch.sqlite3',
            'text-dispatch.sqlite3': state / 'cas-supervisor/operations/caspi-text-dispatch.sqlite3',
            'namseon.db': home / 'waterbe/instances/sales/namseon/namseon_sales.db',
        }
        for name, source in databases.items():
            if not source.is_file():
                raise RuntimeError('backup_source_missing:' + name)
            with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original:
                with closing(sqlite3.connect(target / name)) as copy:
                    original.backup(copy)
                    if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise RuntimeError('backup_integrity_failed:' + name)
        for name in ('config.json', 'state.json', 'outbox.json', 'operation-state.json', 'thinkpad-migration-test.json'):
            source = state / 'waterbe-central/telegram-failure-reporter' / name
            shutil.copy2(source, target / ('telegram-' + name))
        config_target = target / 'cas-config'
        config_target.mkdir()
        for source in (state / 'cas-central').glob('*config.json'):
            shutil.copy2(source, config_target / source.name)
        shutil.copytree(state / 'cas-supervisor/snapshots', target / 'snapshots',
                        ignore=shutil.ignore_patterns('*.partial', '*.tmp'))
        shutil.copytree(state / 'cas-supervisor/operations', target / 'operation-evidence',
                        ignore=shutil.ignore_patterns('*.sqlite3*', '*.tmp', '*.lock'))
        manager_evidence = state / 'waterbe-history/manager-evidence'
        if manager_evidence.is_dir():
            shutil.copytree(manager_evidence, target / 'manager-evidence',
                            ignore=shutil.ignore_patterns('*.partial', '*.tmp'))
        supervisor_config = home / '.local/lib/cas-supervisor-20261005/config'
        for name in ('stores.json', 'scale-product-change-sync.json', 'store-scale-sync.json'):
            shutil.copy2(supervisor_config / name, config_target / name)
        shutil.copytree(home / '.config/systemd/user', target / 'units',
                        ignore=lambda path, names: [name for name in names if not name.startswith(('waterbe-', 'cas-', 'caspi-')) or not name.endswith(('.service', '.timer'))])
        # Preserve the explicitly installed Python releases, not env files or keys.
        for name in ('waterbe-history', 'waterbe-history-low-io-v1',
                     'cas-central-20261005', 'cas-central-adaptive-20261006'):
            release = home / '.local/lib' / name
            if release.is_dir():
                bundle = target / 'runtime' / name
                bundle.mkdir(parents=True)
                for source in release.glob('*.py'):
                    shutil.copy2(source,bundle/source.name)
        hashes = {}
        for path in target.rglob('*'):
            if path.is_file():
                with path.open('rb') as stream:
                    hashes[str(path.relative_to(target))] = hashlib.file_digest(stream, 'sha256').hexdigest()
        manifest = {'created_at': stamp, 'database_integrity': 'verified', 'credentials_included': False, 'hashes': hashes}
        (target / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding='utf-8')
        for path in target.rglob('*'):
            os.chmod(path, 0o700 if path.is_dir() else 0o600)
        complete = target.with_name(stamp)
        target.rename(complete)
        print(json.dumps({'backup': str(complete), 'verified_databases': len(databases), 'files': len(hashes), 'credentials_included': False}))

if __name__ == '__main__':
    main()
