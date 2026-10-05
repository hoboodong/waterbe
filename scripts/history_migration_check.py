"""Read-only migration checks; never prints credentials or source rows."""
import argparse
import sqlite3
from pathlib import Path
from contextlib import closing

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path)
    parser.add_argument('--backup', type=Path)
    parser.add_argument('--cloud', action='store_true')
    parser.add_argument('--read-queue', action='store_true')
    args = parser.parse_args()
    if args.read_queue:
        import history_worker
        try:
            rows = history_worker.rest('GET', 'caspi_remote_read_requests?select=operation_id,status&status=eq.processing')
            print('processing_reads', len(rows))
            if rows:
                return 2
        except Exception as error:
            print('queue_check_failed', type(error).__name__)
            return 1
    if args.cloud:
        import history_worker
        try:
            rows = history_worker.rest('GET', 'waterbe_history_worker_status?select=*&limit=1')
            print('cloud_read_verified', len(rows))
        except Exception as error:
            print('cloud_read_failed', type(error).__name__)
            return 1
    if args.database:
        with closing(sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro', uri=True)) as db:
            if args.backup:
                if args.backup.exists():
                    raise ValueError('Backup destination exists')
                with closing(sqlite3.connect(args.backup)) as target:
                    db.backup(target)
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            print('integrity_verified', db.execute('SELECT count(*) FROM events').fetchone()[0])
            print('pending', db.execute('SELECT count(*) FROM delivery WHERE delivered_at IS NULL').fetchone()[0])
            print('quarantined', db.execute('SELECT count(*) FROM quarantine').fetchone()[0])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
