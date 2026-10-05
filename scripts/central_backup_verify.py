"""Independently verify a completed central backup without starting workers."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument('backup', type=Path)
args = parser.parse_args()
root = args.backup.resolve()
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
for relative, expected in manifest['hashes'].items():
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise SystemExit('Invalid backup entry')
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
            raise SystemExit('Backup hash mismatch')
databases = ['history.db', 'aggregate.sqlite3', 'receipt.sqlite3', 'dispatch.sqlite3', 'text-dispatch.sqlite3', 'namseon.db']
for name in databases:
    with sqlite3.connect((root / name).as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise SystemExit('Backup database invalid')
print(json.dumps({'verified_files': len(manifest['hashes']), 'verified_databases': len(databases), 'workers_started': False}))
