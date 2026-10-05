"""Explicit SQLite online backup for central-worker migration."""
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('source', type=Path)
parser.add_argument('destination', type=Path)
args = parser.parse_args()
if not args.source.is_file() or args.destination.exists():
    raise SystemExit('Source missing or destination exists')
with closing(sqlite3.connect(args.source.resolve().as_uri()+'?mode=ro',uri=True)) as source:
    with closing(sqlite3.connect(args.destination)) as destination:
        source.backup(destination)
        assert destination.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        print('backup_integrity_verified')
