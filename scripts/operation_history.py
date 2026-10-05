"""Append-only operational evidence. Local foundation, not a deployed collector."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3

SOURCES = {'seacode', 'caspi', 'cas_central', 'namseon_sales', 'daeyoung_sales',
           'waterbe', 'deployment'}
KINDS = {'request', 'result', 'observation', 'change', 'incident', 'recovery'}
RESULTS = {'pending', 'succeeded', 'failed', 'uncertain', 'observed'}
FIELDS = {'event_id', 'source', 'kind', 'result', 'feature', 'target', 'store',
          'operation_id', 'occurred_at', 'last_confirmed_at', 'observed_at',
          'actor', 'route', 'rule_version', 'changes', 'evidence_ids'}
# Values must be approved business fields, never arbitrary logs/headers/errors.
CHANGE_FIELDS = {'name', 'price', 'product_code', 'origin', 'importer', 'retailer',
                 'storage', 'product_name_1', 'product_name_2', 'product_name_3',
                 'product_name_4', 'product_name_5', 'ingredients_number',
                 'advertising_number', 'ingredient_text', 'advertising_text',
                 'label_format', 'quantity', 'amount', 'discount', 'status',
                 'recipe_version', 'cost', 'source_version', 'release_version',
                 'artifact_sha256','active','deleted_at'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone required')
    return parsed.astimezone(timezone.utc).isoformat(timespec='microseconds')


def validate(event):
    if not isinstance(event, dict) or set(event) - FIELDS:
        raise ValueError('Unknown event fields; raw logs and credentials are not accepted')
    event = dict(event)
    for key in ('event_id', 'source', 'kind', 'result', 'feature', 'target', 'observed_at'):
        if not isinstance(event.get(key), str) or not event[key] or len(event[key]) > 256:
            raise ValueError('Required event identity missing or invalid')
    if event['source'] not in SOURCES or event['kind'] not in KINDS or event['result'] not in RESULTS:
        raise ValueError('Invalid source/kind/result')
    for key in ('occurred_at', 'last_confirmed_at', 'observed_at'):
        if event.get(key) is not None:
            event[key] = timestamp(event[key])
    if event.get('occurred_at') and event['occurred_at'] > event['observed_at']:
        raise ValueError('Occurrence cannot follow observation')
    if event.get('last_confirmed_at') and event['last_confirmed_at'] > event['observed_at']:
        raise ValueError('Confirmation cannot follow observation')
    for key in ('actor', 'route', 'rule_version', 'operation_id', 'store'):
        if event.get(key) is not None and (not isinstance(event[key], str) or len(event[key]) > 256):
            raise ValueError('Invalid metadata')
    evidence = event.get('evidence_ids', [])
    if not isinstance(evidence, list) or len(evidence) > 100 or any(
            not isinstance(item, str) or not item or len(item) > 256 for item in evidence):
        raise ValueError('Evidence must be bounded opaque IDs, not URLs or file contents')
    if any('://' in item or '?' in item for item in evidence):
        raise ValueError('Evidence URLs are not accepted')
    changes = event.get('changes', [])
    if not isinstance(changes, list) or len(changes) > 100:
        raise ValueError('Invalid changes')
    for change in changes:
        if not isinstance(change, dict) or set(change) != {'field', 'before', 'after'} or change['field'] not in CHANGE_FIELDS:
            raise ValueError('Unapproved change field')
        for key in ('before', 'after'):
            value = change[key]
            if value is not None and not isinstance(value, (str, int, float, bool)):
                raise ValueError('Only scalar business values allowed')
            if isinstance(value, str) and len(value) > 2048:
                raise ValueError('Business value too long')
    if event['result'] == 'succeeded' and event['kind'] in {'result', 'recovery'} and not evidence:
        raise ValueError('Success requires evidence IDs')
    if event['kind'] == 'change' and not changes:
        raise ValueError('Change requires before/after fields')
    if len(canonical(event).encode('utf-8')) > 65536:
        raise ValueError('Event too large')
    return event


def connect(path, write=False):
    path = Path(path).resolve()
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path, timeout=10)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('''CREATE TABLE IF NOT EXISTS events (
            sequence INTEGER PRIMARY KEY, source TEXT NOT NULL, event_id TEXT NOT NULL,
            store TEXT, feature TEXT NOT NULL, target TEXT NOT NULL, operation_id TEXT,
            kind TEXT NOT NULL, result TEXT NOT NULL, observed_at TEXT NOT NULL,
            received_at TEXT NOT NULL, content_hash TEXT NOT NULL, body TEXT NOT NULL,
            UNIQUE(source,event_id))''')
        db.execute('CREATE INDEX IF NOT EXISTS events_time ON events(observed_at,sequence)')
        for action in ('UPDATE', 'DELETE'):
            db.execute(f"CREATE TRIGGER IF NOT EXISTS deny_{action.lower()} BEFORE {action} ON events BEGIN SELECT RAISE(ABORT,'append_only'); END")
        db.commit()
    else:
        db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def append(path, event):
    event = validate(event)
    body = canonical(event)
    digest = hashlib.sha256(body.encode('utf-8')).hexdigest()
    with closing(connect(path, write=True)) as db, db:
        # Serialize the identity check and insertion across concurrent producers.
        db.execute('BEGIN IMMEDIATE')
        prior = db.execute('SELECT content_hash FROM events WHERE source=? AND event_id=?',
                           (event['source'], event['event_id'])).fetchone()
        if prior:
            if prior['content_hash'] != digest:
                raise ValueError('Event identity conflict; original retained')
            return {'status': 'duplicate', 'content_hash': digest}
        db.execute('''INSERT INTO events(source,event_id,store,feature,target,operation_id,
            kind,result,observed_at,received_at,content_hash,body) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
            (event['source'], event['event_id'], event.get('store'), event['feature'], event['target'],
             event.get('operation_id'), event['kind'], event['result'], event['observed_at'],
             datetime.now(timezone.utc).isoformat(), digest, body))
    return {'status': 'stored', 'content_hash': digest}


def query(path, *, after=0, limit=100, since=None, until=None, **filters):
    if not 1 <= limit <= 500 or after < 0:
        raise ValueError('Invalid page bounds')
    clauses, values = ['sequence > ?'], [after]
    for key, value in filters.items():
        if key not in {'source', 'store', 'feature', 'target', 'operation_id', 'kind', 'result'}:
            raise ValueError('Invalid query filter')
        if value is not None:
            clauses.append(key + '=?')
            values.append(value)
    for value, operator in ((since, '>='), (until, '<=')):
        if value:
            clauses.append('observed_at' + operator + '?')
            values.append(timestamp(value))
    if not Path(path).exists():
        return {'status': 'unavailable', 'reason': 'History store not configured/initialized; no zero inferred'}
    db = connect(path)
    try:
        rows = db.execute('SELECT sequence,received_at,content_hash,body FROM events WHERE '
                          + ' AND '.join(clauses) + ' ORDER BY sequence LIMIT ?', values + [limit + 1]).fetchall()
    finally:
        db.close()
    items = [{**json.loads(row['body']), 'sequence': row['sequence'],
              'received_at': row['received_at'], 'content_hash': row['content_hash']} for row in rows[:limit]]
    return {'status': 'available', 'events': items, 'has_more': len(rows) > limit,
            'next_after': items[-1]['sequence'] if items else after,
            'coverage': 'Only explicitly connected producers; absence is not proof of no changes'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=os.environ.get('WATERBE_HISTORY_DB'))
    commands = parser.add_subparsers(dest='command', required=True)
    put = commands.add_parser('append')
    put.add_argument('--event-file', required=True, type=Path)
    read = commands.add_parser('query')
    for key in ('source', 'store', 'feature', 'target', 'operation_id', 'kind', 'result', 'since', 'until'):
        read.add_argument('--' + key.replace('_', '-'))
    read.add_argument('--after', type=int, default=0)
    read.add_argument('--limit', type=int, default=100)
    args = vars(parser.parse_args())
    try:
        path, command = args.pop('database'), args.pop('command')
        if not path:
            raise ValueError('Explicit database path or WATERBE_HISTORY_DB required')
        output = append(path, json.loads(args['event_file'].read_text(encoding='utf-8'))) if command == 'append' else query(path, **args)
    except (ValueError, OSError, sqlite3.Error, TypeError):
        output = {'status': 'unavailable', 'reason': 'Configuration, input or storage validation failed; original retained'}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output['status'] in {'available', 'stored', 'duplicate'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
