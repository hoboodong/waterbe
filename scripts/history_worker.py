"""Read source projections, preserve observed versions, deliver to shared history.

Never executes scale commands or changes a source business table.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import operation_history as history

STORES = ('wangsimni', 'mapo', 'mia', 'wolgye', 'mooner')


def sources():
    entries = []
    for store in STORES:
        entries.extend([
            dict(table='products_' + store, source='seacode', store=store, feature='app.product',
                 identity=['id'], clock='updated_at', fields={'name': 'name', 'retail_price': 'price',
                 'mart_code': 'product_code', 'is_operating': 'status',
                 'is_active':'active','deleted_at':'deleted_at'}),
            dict(table='print_records_' + store, source='seacode', store=store, feature='app.print',
                 identity=['id'], clock='updated_at', fields={'product_name': 'name',
                 'label_count': 'quantity', 'final_price': 'amount', 'discount_rate': 'discount', 'is_void': 'status'}),
            dict(table='scale_product_snapshots_' + store, source='cas_central', store=store,
                 feature='scale.product', identity=['department_number','plu_number'],
                 clock='captured_at', fields={'fields': '_scale'})])
    entries.extend([
        dict(table='scale_text_snapshots', source='cas_central', feature='scale.text',
             identity=['store_id','text_type','text_number'], clock='captured_at',
             fields={'content': 'ingredient_text', 'presence': 'status'}),
        dict(table='operation_diagnostics', source='seacode', feature='app.diagnostic',
             identity=['id'], clock='occurred_at', fields={'result': 'status', 'stage': 'name'},
             metadata=['store_id','operation_id','route']),
        dict(table='caspi_operation_receipts', source='caspi', feature='scale.receipt',
             identity=['operation_id'], clock='published_at', fields={'receipt_hash': 'source_version'},
             metadata=['store_id','operation_id']),
        dict(table='namseon_sales_sources', source='namseon_sales', feature='sales.source',
             identity=['file_id'], clock='imported_at', fields={'modified_time':'source_version','row_count':'quantity'}),
        dict(table='daeyoung_sales_sources', source='daeyoung_sales', feature='sales.source',
             identity=['file_id'], clock='imported_at', fields={'validation_status':'status',
             'calculated_total':'amount','row_count':'quantity'})])
    return entries


def rest(method, route, payload=None):
    base = os.environ.get('SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
    if not base.startswith('https://') or not key:
        raise ValueError('Configured Supabase service environment required')
    request = Request(base + '/rest/v1/' + route, method=method,
                      data=history.canonical(payload).encode() if payload is not None else None,
                      headers={'apikey': key, 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def read_source(entry, since=None):
    columns = sorted(set(entry['identity'] + [entry['clock']] + list(entry['fields']) + entry.get('metadata', [])))
    if entry['table'] == 'scale_text_snapshots':
        columns += ['store_id','text_type']
    rows = []
    for offset in range(0, 200000, 500):
        options=dict(select=','.join(columns),order=','.join(entry['identity']),offset=offset,limit=500)
        if since:
            options[entry['clock']]='gte.'+since
        page = rest('GET', entry['table'] + '?' + urlencode(options))
        if not isinstance(page, list):
            raise ValueError('Invalid source response')
        rows.extend(page)
        if len(page) < 500:
            return rows
    raise ValueError('Source pagination incomplete')


def project(entry, row):
    values = {}
    for key, name in entry['fields'].items():
        if name == '_scale':
            for field in row[key]:
                if field['semantic_key'] in history.CHANGE_FIELDS:
                    values[field['semantic_key']] = field.get('value')
                elif field['semantic_key'] == 'normal_price':
                    values['price'] = field.get('value')
        else:
            if entry['table'] == 'scale_text_snapshots' and key == 'content' and row['text_type'] == 'advertising':
                name = 'advertising_text'
            values[name] = row.get(key)
    return values


def initialize(path):
    with closing(history.connect(path, write=True)) as db, db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS source_state (identity TEXT PRIMARY KEY, version TEXT NOT NULL, body TEXT NOT NULL, observed_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS delivery (sequence INTEGER PRIMARY KEY, delivered_at TEXT, attempts INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS coverage (source TEXT PRIMARY KEY, checked_at TEXT NOT NULL, success_at TEXT, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS quarantine (identity TEXT PRIMARY KEY, detected_at TEXT NOT NULL, code TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, body TEXT NOT NULL, logged INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS health (source TEXT PRIMARY KEY, failures INTEGER NOT NULL, opened INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS polling (source TEXT PRIMARY KEY, full_success_at TEXT NOT NULL);
        ''')


def ingest(path, entry, rows, observed_at):
    stored = 0
    with closing(history.connect(path, write=True)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        for row in rows:
            identity = entry['table'] + ':' + history.canonical([row.get(key) for key in entry['identity']])
            try:
                if any(row.get(key) is None for key in entry['identity']):
                    raise ValueError('Missing identity')
                values = project(entry, row)
                version = hashlib.sha256(history.canonical(values).encode()).hexdigest()
                prior = db.execute('SELECT * FROM source_state WHERE identity=?', (identity,)).fetchone()
                if prior and prior['version'] == version:
                    db.execute('UPDATE source_state SET observed_at=? WHERE identity=?', (observed_at, identity))
                    continue
                before = json.loads(prior['body']) if prior else {}
                baseline = not prior or any(key not in before for key in values)
                event = dict(event_id=hashlib.sha256((identity + (prior['version'] if prior else '') + version + observed_at).encode()).hexdigest(),
                             source=entry['source'], kind='observation' if baseline else 'change', result='observed',
                             feature=entry['feature'], target=identity, observed_at=observed_at, rule_version='history-v1',
                             route='source_observation', evidence_ids=['source:' + hashlib.sha256(identity.encode()).hexdigest()],
                             changes=[dict(field=k, before=before.get(k), after=v) for k,v in values.items() if not prior or before.get(k) != v])
                store = entry.get('store') or row.get('store_id')
                if store:
                    event['store'] = store
                if row.get('operation_id'):
                    event['operation_id'] = row['operation_id']
                if prior:
                    event['last_confirmed_at'] = prior['observed_at']
                # Source update timestamps are metadata, not verified action timestamps.
                event = history.validate(event)
                body = history.canonical(event)
                digest = hashlib.sha256(body.encode()).hexdigest()
                cursor = db.execute('''INSERT INTO events(source,event_id,store,feature,target,operation_id,kind,result,
                    observed_at,received_at,content_hash,body) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (event['source'],event['event_id'],event.get('store'),event['feature'],identity,event.get('operation_id'),
                     event['kind'],event['result'],event['observed_at'],observed_at,digest,body))
                db.execute('INSERT INTO delivery(sequence) VALUES(?)', (cursor.lastrowid,))
                db.execute('INSERT OR REPLACE INTO source_state VALUES(?,?,?,?)', (identity,version,history.canonical(values),observed_at))
                stored += 1
            except (ValueError, KeyError, TypeError):
                db.execute('INSERT OR REPLACE INTO quarantine VALUES(?,?,?)', (identity,observed_at,'projection_invalid'))
    return stored


def deliver(path, limit=100):
    with closing(history.connect(path)) as db:
        pending = db.execute('SELECT e.sequence,e.body FROM events e JOIN delivery d USING(sequence) WHERE d.delivered_at IS NULL ORDER BY d.attempts,e.sequence LIMIT ?', (limit,)).fetchall()
    if not pending:
        return 0
    events = [json.loads(row['body']) for row in pending]
    try:
        acknowledgments = rest('POST', 'rpc/append_waterbe_history_batch', {'p_events': events})
        if not isinstance(acknowledgments,list):
            raise ValueError('Invalid acknowledgment')
        accepted = {(ack['source'],ack['event_id']) for ack in acknowledgments
                    if ack.get('status') in {'stored','duplicate'}}
    except Exception:
        accepted = set()
    sent = 0
    with closing(history.connect(path, write=True)) as db, db:
        for row,event in zip(pending,events):
            good = (event['source'],event['event_id']) in accepted
            db.execute('UPDATE delivery SET delivered_at=?,attempts=attempts+1 WHERE sequence=?',
                       (datetime.now(timezone.utc).isoformat() if good else None,row['sequence']))
            sent += int(good)
    return sent


def status(path):
    with closing(history.connect(path)) as db:
        return dict(coverage=[dict(r) for r in db.execute('SELECT * FROM coverage ORDER BY source')],
                    pending=db.execute('SELECT count(*) FROM delivery WHERE delivered_at IS NULL').fetchone()[0],
                    quarantined=db.execute('SELECT count(*) FROM quarantine').fetchone()[0])


def file_versions(path, root):
    entry=dict(table='waterbe_master_files',source='waterbe',feature='business.file',
               identity=['id'],clock='updated_at',fields={'version':'source_version'})
    rows=[]
    for file in (Path(root)/'instances/master').rglob('*.yaml'):
        rows.append(dict(id=file.relative_to(root).as_posix(),
                         version=hashlib.sha256(file.read_bytes()).hexdigest()))
    if not rows:
        raise ValueError('Configured business source files missing')
    return ingest(path,entry,rows,datetime.now(timezone.utc).isoformat(timespec='microseconds'))


def release_version(path):
    base=os.environ.get('SUPABASE_URL','').rstrip('/')
    if not base.startswith('https://'):
        raise ValueError('Configured release source required')
    with urlopen(base+'/storage/v1/object/public/app-releases/latest.json?history='+str(int(time.time())),timeout=20) as response:
        value=json.load(response)
    if not isinstance(value.get('versionCode'),int) or not isinstance(value.get('versionName'),str):
        raise ValueError('Invalid release pointer')
    entry=dict(table='app_release_pointer',source='deployment',feature='deployment.pointer',
               identity=['id'],clock='observed_at',fields={'version':'release_version','commit':'source_version'})
    row=dict(id='app-releases/latest',version=value['versionName']+' / '+str(value['versionCode']),commit=value.get('sourceCommit'))
    return ingest(path,entry,[row],datetime.now(timezone.utc).isoformat(timespec='microseconds'))


def backup(path):
    destination=Path(path).parent/'backups'/datetime.now(timezone.utc).strftime('%Y%m%d')/'operations.db'
    if destination.exists():
        return
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_suffix('.pending')
    with closing(history.connect(path)) as source, closing(sqlite3.connect(temporary)) as target:
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('Backup integrity failure')
    temporary.replace(destination)


def health_notice(path,source,good,now):
    with closing(history.connect(path,write=True)) as db,db:
        old=db.execute('SELECT failures,opened FROM health WHERE source=?',(source,)).fetchone()
        failures=0 if good else (old['failures'] if old else 0)+1
        opened=old['opened'] if old else 0
        status=None
        if not good and failures>=2 and not opened:
            opened=1
            status='failed'
        elif good and opened:
            opened=0
            status='recovered'
        db.execute('INSERT OR REPLACE INTO health VALUES(?,?,?)',(source,failures,opened))
        if status:
            body=dict(event='waterbe_history_health',status=status,source=source,
                      timestamp=now.replace('+00:00','Z'))
            identity=hashlib.sha256(history.canonical(body).encode()).hexdigest()
            db.execute('INSERT OR IGNORE INTO notices(id,body) VALUES(?,?)',(identity,history.canonical(body)))
            event=history.validate(dict(event_id=identity,source='waterbe',
                kind='incident' if status=='failed' else 'recovery',
                result='failed' if status=='failed' else 'observed',feature='history.health',
                target=source,observed_at=now,route='source_observation',rule_version='history-v1',
                changes=[dict(field='status',before='available' if status=='failed' else 'unavailable',
                              after='unavailable' if status=='failed' else 'available')]))
            encoded=history.canonical(event)
            cursor=db.execute('''INSERT INTO events(source,event_id,feature,target,kind,result,
                observed_at,received_at,content_hash,body) VALUES(?,?,?,?,?,?,?,?,?,?)''',
                (event['source'],identity,event['feature'],source,event['kind'],event['result'],
                 event['observed_at'],now,hashlib.sha256(encoded.encode()).hexdigest(),encoded))
            db.execute('INSERT INTO delivery(sequence) VALUES(?)',(cursor.lastrowid,))


def publish_notices(path,root):
    if not root:
        return
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    with closing(history.connect(path)) as db:
        rows=db.execute('SELECT id,body FROM notices WHERE logged=0').fetchall()
    for row in rows:
        day=datetime.now(timezone.utc).strftime('%Y%m%d')
        with (root/('worker-history-'+day+'.jsonl')).open('a',encoding='utf-8') as output:
            output.write(row['body']+'\n')
            output.flush()
            os.fsync(output.fileno())
        with closing(history.connect(path,write=True)) as db,db:
            db.execute('UPDATE notices SET logged=1 WHERE id=?',(row['id'],))


def polling_interval(entry):
    if entry['table'].startswith('products_'):
        return 300
    if entry['table'].startswith('scale_') or entry['table'].endswith('_sales_sources'):
        return 900
    return 60


def polling_plan(entry, previous, last_full, now):
    """Due/fallback policy; never advance a cursor on failed reads or skipped work."""
    if not previous or not previous['success_at']:
        return True, None
    moment = datetime.fromisoformat(now)
    success = datetime.fromisoformat(previous['success_at'])
    if previous['status'] == 'available' and (moment - success).total_seconds() < polling_interval(entry):
        return False, None
    full = datetime.fromisoformat(last_full or previous['success_at'])
    if (moment - full).total_seconds() >= 86400:
        return True, None
    return True, (success - timedelta(minutes=10)).isoformat()


def once(path,source_root=None,notification_root=None):
    initialize(path)
    total = 0
    polling = dict(queried=0, skipped=0, incremental=0, full=0, policy='low-io-v1')
    for entry in sources():
        now = datetime.now(timezone.utc).isoformat(timespec='microseconds')
        ok = False
        try:
            with closing(history.connect(path)) as db:
                previous=db.execute('SELECT success_at,status FROM coverage WHERE source=?',(entry['table'],)).fetchone()
                last_full=db.execute('SELECT full_success_at FROM polling WHERE source=?',(entry['table'],)).fetchone()
            due, since = polling_plan(entry, previous, last_full['full_success_at'] if last_full else None, now)
            if not due:
                polling['skipped'] += 1
                continue  # Keep actual observation timestamps; do not manufacture freshness.
            polling['queried'] += 1
            polling['full' if since is None else 'incremental'] += 1
            total += ingest(path, entry, read_source(entry,since), now)
            ok = True
            with closing(history.connect(path,write=True)) as db, db:
                if since is None:
                    db.execute('INSERT OR REPLACE INTO polling VALUES(?,?)',(entry['table'],now))
                elif not last_full:
                    db.execute('INSERT OR IGNORE INTO polling VALUES(?,?)',(entry['table'],previous['success_at']))
        except Exception:
            pass  # Never emit source response bodies or secrets.
        with closing(history.connect(path, write=True)) as db, db:
            db.execute('''INSERT INTO coverage VALUES(?,?,?,?) ON CONFLICT(source) DO UPDATE SET
                checked_at=excluded.checked_at,success_at=coalesce(excluded.success_at,coverage.success_at),status=excluded.status''',
                (entry['table'],now,now if ok else None,'available' if ok else 'unavailable'))
        health_notice(path,entry['table'],ok,now)
    delivered = deliver(path, limit=500)
    now=datetime.now(timezone.utc).isoformat(timespec='microseconds')
    good=False
    try:
        total+=release_version(path)
        good=True
    except Exception:
        pass
    health_notice(path,'app_release_pointer',good,now)
    with closing(history.connect(path,write=True)) as db,db:
        db.execute('INSERT OR REPLACE INTO coverage VALUES(?,?,?,?)',
                   ('app_release_pointer',now,now if good else None,'available' if good else 'unavailable'))
    if source_root:
        now=datetime.now(timezone.utc).isoformat(timespec='microseconds')
        good=False
        try:
            total+=file_versions(path,source_root)
            good=True
        except Exception:
            pass
        with closing(history.connect(path,write=True)) as db,db:
            db.execute('INSERT OR REPLACE INTO coverage VALUES(?,?,?,?)',
                       ('waterbe_master_files',now,now if good else None,'available' if good else 'unavailable'))
    state=status(path)
    state['polling'] = polling
    try:
        publish_notices(path,notification_root)
    except Exception:
        state['notification_publication']='unavailable'
    try:
        backup(path)
        state['backup']='verified'
    except Exception:
        state['backup']='unavailable'
    try:
        rest('POST','rpc/set_waterbe_history_status',{'p_status':state})
    except Exception:
        state['status_publication']='unavailable'
    return dict(stored=total, delivered=delivered, **state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--source-root',type=Path)
    parser.add_argument('--notification-root',type=Path)
    parser.add_argument('command', choices=['once','watch','status','drain'])
    args = parser.parse_args()
    if args.command == 'status':
        print(json.dumps(status(args.database), ensure_ascii=False))
    elif args.command == 'once':
        print(json.dumps(once(args.database,args.source_root,args.notification_root), ensure_ascii=False))
    elif args.command=='drain':
        while status(args.database)['pending']:
            if not deliver(args.database,500):
                break
        print(json.dumps(status(args.database),ensure_ascii=False))
    else:
        while True:
            try:
                cycle = once(args.database,args.source_root,args.notification_root)
                print(json.dumps({'event':'history_poll_cycle','polling':cycle['polling'],
                                  'stored':cycle['stored'],'delivered':cycle['delivered']}),flush=True)
                health_notice(args.database,'history_worker',True,
                              datetime.now(timezone.utc).isoformat(timespec='microseconds'))
                publish_notices(args.database,args.notification_root)
            except Exception:
                # Retain internal cycle failure; never silently label a stale cycle healthy.
                health_notice(args.database,'history_worker',False,
                              datetime.now(timezone.utc).isoformat(timespec='microseconds'))
                publish_notices(args.database,args.notification_root)
            time.sleep(60)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
