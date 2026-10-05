import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux central backup')
class CentralBackupTests(unittest.TestCase):
    def test_wal_connections_closed_before_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            database_paths = ['.local/state/waterbe-history/operations.db',
                '.local/state/cas-central/aggregate-central.sqlite3',
                '.local/state/cas-central/receipt-state.sqlite3',
                '.local/state/cas-supervisor/operations/caspi-remote-dispatch.sqlite3',
                '.local/state/cas-supervisor/operations/caspi-text-dispatch.sqlite3',
                'waterbe/instances/sales/namseon/namseon_sales.db']
            for relative in database_paths:
                path = home / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                db = sqlite3.connect(path)
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE sample(id INTEGER)')
                db.execute('INSERT INTO sample VALUES(1)')
                db.commit()
                db.close()
            reporter = home / '.local/state/waterbe-central/telegram-failure-reporter'
            reporter.mkdir(parents=True)
            for name in ('config.json','state.json','outbox.json','operation-state.json','thinkpad-migration-test.json'):
                (reporter / name).write_text('{}')
            (home / '.local/state/cas-supervisor/snapshots').mkdir()
            (home / '.config/systemd/user').mkdir(parents=True)
            config = home / '.local/lib/cas-supervisor-20261005/config'
            config.mkdir(parents=True)
            for name in ('stores.json','scale-product-change-sync.json','store-scale-sync.json'):
                (config / name).write_text('{}')
            result = subprocess.run([sys.executable, str(ROOT/'scripts/central_backup.py'), '--home', str(home)],
                                    capture_output=True, text=True, check=True)
            backup = Path(json.loads(result.stdout)['backup'])
            manifest = json.loads((backup/'manifest.json').read_text())
            self.assertFalse(any(name.endswith(('-wal','-shm')) for name in manifest['hashes']))
            subprocess.run([sys.executable,str(ROOT/'scripts/central_backup_verify.py'),str(backup)],
                           capture_output=True, check=True)
            (backup/'history.db').write_bytes(b'corrupted')
            rejected = subprocess.run([sys.executable,str(ROOT/'scripts/central_backup_verify.py'),str(backup)], capture_output=True)
            self.assertNotEqual(rejected.returncode,0)

if __name__ == '__main__':
    unittest.main()
