"""Typed adapters to existing operations; no general shell or second scale writer.

Jobs survive MCP disconnects. A claimed job is never automatically executed twice.
Business success remains the owning executor's ACK/read-back/publication result.
"""
from __future__ import annotations
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import uuid
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT=Path(os.environ.get('WATERBE_ROOT',Path(__file__).resolve().parents[1])).resolve()
STATE=Path.home()/'.local/state/waterbe-mcp'
STORES=('wangsimni','mapo','mia','wolgye','mooner')
FIELDS={'classification','plu_type','normal_price','product_code','valid_days',
        'ingredients_number','processing_time_display','advertising_number','tare',
        'quantity_unit_number',*(f'product_name_{i}' for i in range(1,6))}
# Required, optional, effect. Unknown parameters never become CLI arguments.
SPECS={
 'products.read':('store','limit offset','read'),
 'discounts.read':('store business_date','limit offset','read'),
 'diagnostics.read':('store','business_date operation_id feature result limit offset','read'),
 'scale.products.read':('store','limit offset','read'),
 'scale.texts.read':('store','text_type limit offset','read'),
 'scale.work.read':('store','','read'),
 'scale.day.read':('store business_date','offset limit','read'),
 'scale.product.read':('store department record_sequence','','read'),
 'scale.text.read':('store text_type text_number','','read'),
 'scale.operation.read':('store target_operation_id','','read'),
 'scale.collect':('store','','collect'),
 'scale.product.change':('store department plu expected_fields requested_fields base_content_sha256','','write'),
 'scale.text.change':('store text_type text_number operation expected_presence','expected_content requested_content','write'),
 'scale.reconcile':('store target_operation_id kind','','reconcile'),
 'recipes.audit':('','','read'),
 'history.append':('event','','write'),
 'sales.namseon.sync':('','business_date','sync'),
 'sales.daeyoung.sync':('results_root','','sync'),
 'sales.daeyoung.ocr':('input_dir manifest month','','collect'),
 'sales.namseon.month':('store month','','read'),
 'sales.daeyoung.month':('month','','read'),
 'central.check':('','','read'),
 'central.restart':('component','','write'),
 'central.backup':('','','write'),
}
GUIDES={
 'products.read':'docs/guides/STORE_PRODUCTS_GUIDE.md',
 'discounts.read':'docs/guides/DAILY_STORE_REPORT_GUIDE.md',
 'diagnostics.read':'docs/guides/PROGRAM_RESPONSIBILITIES_GUIDE.md',
 'recipes.audit':'docs/guides/RECIPES_COST_GUIDE.md',
 'history.append':'docs/guides/OPERATION_HISTORY_GUIDE.md',
}


def now():
    return datetime.now(timezone.utc).isoformat()


def description(operation):
    required,optional,effect=SPECS[operation]
    return dict(operation=operation,required_parameters=required.split(),
                optional_parameters=optional.split(),effect=effect,
                guide=GUIDES.get(operation,'instances/sales/README.md' if operation.startswith('sales.')
                  else 'docs/guides/THINKPAD_CENTRAL_MANAGEMENT_GUIDE.md' if operation.startswith('central.')
                  else 'docs/guides/SEACODE_SCALE_GUIDE.md'),
                completion='Executor results and source evidence, not job acceptance or process exit alone',
                parameter_rules={key:value for key,value in {
                    'store':list(STORES),'business_date':'YYYY-MM-DD','month':'YYYY-MM',
                    'limit':'integer 1..500, default100','offset':'integer>=0, default0',
                    'text_type':['ingredient','advertising'],'operation':['upsert','delete'],
                    'expected_presence':['value','empty','missing'],
                    'kind':['product','text'],'expected_fields':'current verified values by field',
                    'requested_fields':sorted(FIELDS),'base_content_sha256':'current verified snapshot SHA256',
                    'results_root':'Existing directory below ~/.local/state/waterbe-central',
                    'event':'Existing operation_history event contract; secrets and raw errors forbidden',
                    'input_dir':'Existing OCR source directory below ~/.local/state/waterbe-central',
                    'manifest':'Existing source manifest file below ~/.local/state/waterbe-central',
                }.items() if key in (required+' '+optional).split()})


def validate(operation,p):
    if operation not in SPECS or not isinstance(p,dict):
        raise ValueError('unsupported_operation')
    required,optional,_=SPECS[operation]
    if set(p)-set((required+' '+optional).split()) or set(required.split())-set(p):
        raise ValueError('invalid_parameter_names')
    p=dict(p)
    if len(json.dumps(p).encode())>65536:
        raise ValueError('parameters_too_large')
    if 'store' in p and p['store'] not in STORES:
        raise ValueError('unregistered_store')
    for name in ('business_date','month'):
        if name in p:
            value=p[name]
            pattern=r'\d{4}-\d{2}-\d{2}' if name=='business_date' else r'\d{4}-\d{2}'
            if not isinstance(value,str) or not re.fullmatch(pattern,value):
                raise ValueError('invalid_date')
            date.fromisoformat(value if name=='business_date' else value+'-01')
    for name in ('operation_id','target_operation_id'):
        if name in p:
            p[name]=str(uuid.UUID(p[name]))
    for name,low,high in (('department',0,99),('record_sequence',1,999999),('plu',1,999999),
                          ('text_number',1,9999),('offset',0,1000000),('limit',1,500)):
        if name in p and (type(p[name]) is not int or not low<=p[name]<=high):
            raise ValueError('invalid_'+name)
    if 'text_type' in p and p['text_type'] not in ('ingredient','advertising'):
        raise ValueError('invalid_text_type')
    if 'text_number' in p and p['text_number']>(99 if p['text_type']=='advertising' else 1000):
        raise ValueError('text_number_outside_existing_table')
    if operation=='diagnostics.read' and not (p.get('business_date') or p.get('operation_id')):
        raise ValueError('date_or_operation_required')
    if operation=='scale.product.change':
        before,after=p['expected_fields'],p['requested_fields']
        if (not isinstance(before,dict) or not isinstance(after,dict) or not after
            or set(after)-FIELDS or set(before)-FIELDS or set(after)-set(before)
            or not isinstance(p['base_content_sha256'],str)
            or not re.fullmatch('[0-9a-f]{64}',p['base_content_sha256'])):
            raise ValueError('expected_fields_and_snapshot_hash_required')
        if all(before[k]==v for k,v in after.items()):
            raise ValueError('no_fields_changed')
    if operation=='scale.text.change':
        if p['operation'] not in ('upsert','delete') or p['expected_presence'] not in ('value','empty','missing'):
            raise ValueError('invalid_text_change')
        if p['expected_presence']=='value' and not isinstance(p.get('expected_content'),str):
            raise ValueError('expected_content_required')
        if p['operation']!='delete' and (not isinstance(p.get('requested_content'),str) or not p['requested_content']):
            raise ValueError('requested_content_required')
        if p['operation']=='delete' and p.get('requested_content') is not None:
            raise ValueError('delete_content_must_be_null')
    if operation=='scale.reconcile' and p['kind'] not in ('product','text'):
        raise ValueError('invalid_reconciliation_kind')
    if operation=='central.restart' and p['component'] not in ('history','read','supervisor','aggregate','receipts','reporter','health','backup','sync'):
        raise ValueError('invalid_component')
    if operation=='sales.namseon.month' and p['store'] not in ('wangsimni','mapo','mia'):
        raise ValueError('wrong_sales_source')
    if 'results_root' in p:
        directory=Path(p['results_root']).resolve()
        allowed=Path.home()/'.local/state/waterbe-central'
        if not directory.is_relative_to(allowed) or not directory.is_dir():
            raise ValueError('existing_central_results_directory_required')
        p['results_root']=str(directory)
    if operation=='sales.daeyoung.ocr':
        allowed=Path.home()/'.local/state/waterbe-central'
        for key in ('input_dir','manifest'):
            path=Path(p[key]).resolve()
            if not path.is_relative_to(allowed) or not path.exists():
                raise ValueError('existing_central_input_required')
            p[key]=str(path)
        if not Path(p['input_dir']).is_dir() or not Path(p['manifest']).is_file():
            raise ValueError('invalid_ocr_input_types')
    for name in ('feature','result'):
        if name in p and (not isinstance(p[name],str) or not re.fullmatch('[A-Za-z0-9_.-]{1,80}',p[name])):
            raise ValueError('invalid_filter')
    if operation=='history.append':
        from operation_history import validate as validate_event
        p['event']=validate_event(p['event'])
        if (p['event']['result']=='succeeded' or p['event']['kind']=='recovery') and not p['event'].get('evidence_ids'):
            raise ValueError('success_evidence_required')
    return p


def rest(route,parameters=None,payload=None):
    base=os.environ.get('SUPABASE_URL','').rstrip('/')
    key=os.environ.get('SUPABASE_SERVICE_ROLE_KEY','')
    parsed=urlparse(base)
    if parsed.scheme!='https' or not parsed.netloc or parsed.path or parsed.username or not key:
        raise RuntimeError('configured_service_environment_required')
    url=base+'/rest/v1/'+route+('?' + urlencode(parameters) if parameters else '')
    request=Request(url,data=json.dumps(payload).encode() if payload is not None else None,
                    headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json'},
                    method='POST' if payload is not None else 'GET')
    with urlopen(request,timeout=25) as response:
        return json.load(response)


def read_rows(operation,p):
    limit=p.get('limit',100)
    query={'select':'*','limit':limit+1,'offset':p.get('offset',0),'order':'id'}
    if operation=='products.read':
        table='products_'+p['store']
        query.update(is_active='eq.true',is_operating='eq.true')
    elif operation=='discounts.read':
        table='print_records_'+p['store']
        query['and']=day_filter('printed_at',p['business_date'])
        query['order']='printed_at,id'
    elif operation=='scale.products.read':
        table='scale_product_snapshots_'+p['store']
        query['order']='department_number,plu_number'
    elif operation=='scale.texts.read':
        table='scale_text_snapshots'
        query.update(store_id='eq.'+p['store'],order='text_type,text_number')
        if p.get('text_type'):
            query['text_type']='eq.'+p['text_type']
    else:
        table='operation_diagnostics'
        query.update(store_id='eq.'+p['store'],order='occurred_at,id')
        if p.get('business_date'):
            query['and']=day_filter('occurred_at',p['business_date'])
        for key in ('operation_id','feature','result'):
            if p.get(key):
                query[key]='eq.'+p[key]
    rows=rest(table,query)
    if not isinstance(rows,list):
        raise RuntimeError('invalid_source_response')
    return dict(status='available',source=table,data=rows[:limit],has_more=len(rows)>limit,
                next_offset=p.get('offset',0)+limit if len(rows)>limit else None,
                fetched_at=now(),warnings=['Stored source, not physical scale/phone freshness.',
                'Offset pages may change during concurrent updates; no full-report completeness asserted.'])


def day_filter(field,business_date):
    day=date.fromisoformat(business_date)
    return f'({field}.gte.{day}T00:00:00+09:00,{field}.lt.{day+timedelta(days=1)}T00:00:00+09:00)'


def cli(args,json_output=True):
    # Fixed command construction only; output with arbitrary exception bodies is never returned.
    run=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',cwd=ROOT)
    job=globals().get('CURRENT_JOB')
    if job:
        evidence=STATE/'native-evidence'/job
        evidence.mkdir(parents=True,exist_ok=True,mode=0o700)
        # Protected operator evidence only, never returned as shared history/raw errors.
        (evidence/'stdout.txt').write_text(run.stdout,encoding='utf-8')
        (evidence/'stderr.txt').write_text(run.stderr,encoding='utf-8')
    if run.returncode:
        raise RuntimeError('native_command_failed')
    if json_output:
        return json.loads(run.stdout)
    return {'status':'executor_completed','exit_code':0,
            'verification':'Existing command completed; independently read destination before reporting business success.'}


def caspi(operation,p,operation_id):
    # Use the installed central executor and receipt verifier, not a new protocol implementation.
    native=Path.home()/'.local/lib/cas-central-20261005'
    sys.path.insert(0,str(native))
    from caspi_remote_read_worker import execute,load_config
    from caspi_receipt_sync import _envelope
    config=load_config(Path.home()/'.local/state/cas-central/read-config.json')
    store=next(s for s in config['stores'] if s['enabled'] and s['app_store_id']==p['store'])
    commands={'scale.day.read':'aggregate_day','scale.collect':'collect_aggregate',
              'scale.product.read':'read_plu','scale.text.read':'read_text',
              'scale.operation.read':'operation_status',
              'scale.reconcile':'reconcile_text' if p.get('kind')=='text' else 'reconcile_write'}
    request=dict(type='request',protocol_version=1,operation_id=p['target_operation_id'] if operation=='scale.operation.read' else operation_id,
                 store_id=store['controller_store_id'],origin='central_remote',command=commands[operation])
    for key in ('business_date','department','record_sequence','text_type','text_number','target_operation_id'):
        if key in p and operation!='scale.operation.read':
            request[key]=p[key]
    if operation=='scale.day.read':
        request.update(offset=p.get('offset',0),limit=p.get('limit',100))
    receipt=execute(store['ssh_alias'],request,float(config['ssh_timeout_seconds']))
    if (receipt.get('operation_id')!=request['operation_id'] or receipt.get('store_id')!=request['store_id']
        or (operation!='scale.operation.read' and receipt.get('command')!=request['command'])):
        raise RuntimeError('receipt_identity_invalid')
    if operation=='scale.operation.read':
        return {'status':receipt.get('status','execution_unknown'),'receipt':receipt,
                'warning':'Original immutable receipt only; no write replay or new publication.'}
    envelope=_envelope(store['controller_store_id'],request,receipt)
    # Same publisher as the existing central worker. Publication is separate evidence.
    try:
        ack=rest('rpc/publish_caspi_receipt_from_central',payload={'p_store_id':p['store'],'p_operation':envelope})
    except Exception:
        return {'status':'publication_unconfirmed','receipt':receipt,'operation_id':operation_id,
                'warning':'Device receipt retained; check original ID, never replay the device operation.'}
    if not isinstance(ack,dict) or ack.get('stored') is not True or ack.get('operation_id')!=operation_id:
        return {'status':'publication_unconfirmed','receipt':receipt,'operation_id':operation_id}
    return {'status':receipt.get('status','execution_unknown'),'receipt':receipt,'published':True}


def run_action(operation,p,operation_id):
    if operation in ('products.read','discounts.read','diagnostics.read','scale.products.read','scale.texts.read'):
        return read_rows(operation,p)
    if operation=='scale.work.read':
        from phone_work_status import read
        return read(p['store'])
    if operation in ('scale.day.read','scale.product.read','scale.text.read','scale.operation.read','scale.collect','scale.reconcile'):
        return caspi(operation,p,operation_id)
    if operation=='scale.product.change':
        body={'p_store_id':p['store'],'p_department_number':p['department'],'p_plu_number':p['plu'],
              'p_expected_fields':p['expected_fields'],'p_requested_fields':p['requested_fields'],
              'p_client_request_id':operation_id,'p_base_content_sha256':p['base_content_sha256']}
        row=rest('rpc/request_scale_product_change',payload=body)
        return {'status':'accepted','request':safe_request(row),'operation_id':operation_id,
                'warning':'Queued, not scale applied. Poll action status for executor/read-back/publication evidence.'}
    if operation=='scale.text.change':
        body={'p_client_request_id':operation_id,'p_store_id':p['store'],
              **{'p_'+key:p.get(key) for key in ('text_type','text_number','operation','expected_presence','expected_content','requested_content')}}
        row=rest('rpc/request_scale_text_change_idempotent',payload=body)
        return {'status':'accepted','request':safe_request(row),'operation_id':operation_id,
                'warning':'Queued, not applied; require ACK/read-back and app snapshot evidence.'}
    if operation=='recipes.audit':
        return cli([central_python(),str(ROOT/'scripts/inspect_recipe_data.py')])
    if operation=='history.append':
        from operation_history import append,connect
        database=Path.home()/'.local/state/waterbe-history/operations.db'
        # The same event must also enter the existing delivery queue, even after an interrupted append.
        result=append(database,p['event'])
        with closing(connect(database,write=True)) as db,db:
            row=db.execute('SELECT sequence FROM events WHERE source=? AND event_id=?',
                           (p['event']['source'],p['event']['event_id'])).fetchone()
            db.execute('INSERT OR IGNORE INTO delivery(sequence) VALUES(?)',(row['sequence'],))
        return {**result,'publication':'queued_in_existing_history_delivery'}
    central=str(Path.home()/'.local/bin/waterbe-central')
    if operation=='sales.namseon.sync':
        if p.get('business_date'):
            return cli(['flock','-n',str(Path.home()/'.local/state/waterbe-central/namseon-sync.lock'),
                        central_python(),str(ROOT/'scripts/namseon_supabase_sync.py'),'--date',p['business_date']],False)
        return cli([central,'namseon-sync'],False)
    if operation=='sales.daeyoung.sync':
        return cli([central,'daeyoung-publish','--results-root',p['results_root']],False)
    if operation=='sales.daeyoung.ocr':
        output=Path.home()/'.local/state/waterbe-central/mcp-ocr'/operation_id
        output.mkdir(parents=True,exist_ok=False,mode=0o700)
        result=cli([central,'daeyoung-ocr',p['input_dir'],'--manifest',p['manifest'],
                    '--year',p['month'][:4],'--csv',str(output/(p['month']+'_sales.csv')),
                    '--report',str(output/(p['month']+'_report.json'))],False)
        return {**result,'output':str(output),'warning':'OCR result requires validation before publication.'}
    if operation=='sales.namseon.month':
        # Existing CLI prints a human-readable statement, not JSON. Keep a bounded business report.
        run=subprocess.run([central_python(),str(ROOT/'scripts/namseon_sales.py'),'month-total',
                            '--store',p['store'],'--month',p['month']],capture_output=True,text=True,cwd=ROOT)
        if run.returncode:
            raise RuntimeError('native_month_read_failed')
        return {'status':'available','source':'central namseon SQLite','report':run.stdout[:20000],
                'warning':'Cross-check Supabase per sales guide; latest ingestion not asserted.'}
    if operation=='sales.daeyoung.month':
        return cli([central,'daeyoung-month','--month',p['month']])
    if operation=='central.check':
        return cli([central,'manage','check'])
    if operation=='central.restart':
        return cli([central,'manage','restart',p['component'],'--approved'])
    if operation=='central.backup':
        return cli([central,'backup'])
    raise ValueError('unsupported_operation')


def central_python():
    return str(Path.home()/'.local/opt/waterbe-central-venv/bin/python')


def database():
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    db=sqlite3.connect(STATE/'actions.db',timeout=10)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA synchronous=FULL')
    db.execute('''CREATE TABLE IF NOT EXISTS jobs(
        id TEXT PRIMARY KEY, digest TEXT NOT NULL, operation TEXT NOT NULL,
        parameters TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL, pid INTEGER, result TEXT, user_request TEXT NOT NULL)''')
    db.commit()
    (STATE/'actions.db').chmod(0o600)
    return db


def safe_request(row):
    if isinstance(row,list):
        return [safe_request(item) for item in row]
    if not isinstance(row,dict):
        raise ValueError('invalid_request_ack')
    allowed={'id','status','store_id','department_number','plu_number','client_request_id',
             'created_at','updated_at','completed_at','expected_fields','requested_fields',
             'actual_fields','base_content_sha256','text_type','text_number','operation',
             'expected_presence','expected_content','requested_content','actual_presence',
             'actual_content','read_back_verified','operation_id'}
    allowed.update({'requested_at','claimed_at','verified_at','result_fields','failure_code',
                    'retryable','write_started','rollback_status'})
    return {k:v for k,v in row.items() if k in allowed}


def prepare(operation,parameters):
    try:
        p=validate(operation,parameters)
        return {**description(operation),'status':'ready','parameters':p,
                'requires_user_request':SPECS[operation][2]!='read',
                'warning':'Read the guide first. Preparation executes nothing; authorization is not conferred by this result.'}
    except (ValueError,TypeError,KeyError):
        return {'status':'invalid_request','reason':'Check required parameters, registered targets, expectations and date.',
                'contract':description(operation) if operation in SPECS else None}


def check_connections():
    checks={}
    for name,path in {
        'central_launcher':Path.home()/'.local/bin/waterbe-central',
        'central_python':Path(central_python()),
        'caspi_executor':Path.home()/'.local/lib/cas-central-20261005/caspi_remote_read_worker.py',
        'caspi_store_config':Path.home()/'.local/state/cas-central/read-config.json',
        'history_database':Path.home()/'.local/state/waterbe-history/operations.db',
    }.items():
        checks[name]='present' if path.is_file() else 'missing'
    try:
        document=rest('')
        paths=document.get('paths',{})
        checks['supabase_schema']='available'
        checks['existing_write_rpc']={name:('/rpc/'+name) in paths for name in (
            'request_scale_product_change','request_scale_text_change_idempotent',
            'publish_caspi_receipt_from_central')}
    except Exception:
        checks['supabase_schema']='unavailable; no mutation attempted'
    return {'status':'checked','checked_at':now(),'checks':checks,
            'warning':'Presence/access only. No physical writes, synchronization, restart or APK deployment tested.'}


def submit(operation,parameters,operation_id,user_request):
    operation_id=str(uuid.UUID(operation_id))
    p=validate(operation,parameters)
    if not isinstance(user_request,str) or not user_request.strip() or len(user_request)>1000:
        raise ValueError('explicit_user_request_summary_required')
    digest=hashlib.sha256(json.dumps([operation,p],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    with closing(database()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        prior=db.execute('SELECT * FROM jobs WHERE id=?',(operation_id,)).fetchone()
        if prior:
            if prior['digest']!=digest:
                return {'status':'conflict','reason':'Original operation ID has different content; no execution.'}
            return status(operation_id,False)
        # Preserve existing source-level locking too; never overlap two MCP sales ingestions.
        if SPECS[operation][2]=='sync':
            active=db.execute("SELECT id FROM jobs WHERE operation=? AND status IN ('pending','running')",(operation,)).fetchall()
            for job in active:
                phase=status(job['id'],False)['status']
                if phase in ('pending','running'):
                    return {'status':'busy','operation_id':job['id'],
                            'reason':'Same-source sync is active; other sources remain available.'}
        stamp=now()
        db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (operation_id,digest,operation,json.dumps(p,ensure_ascii=False),'pending',stamp,stamp,None,None,user_request))
    try:
        process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--job',operation_id],
                                 stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                 start_new_session=True,env=os.environ.copy())
        with closing(database()) as db,db:
            db.execute('UPDATE jobs SET pid=? WHERE id=?',(process.pid,operation_id))
    except OSError:
        finish(operation_id,{'status':'not_started','reason':'Process launch failed; no automatic replay.'})
    return status(operation_id,False)


def finish(operation_id,result):
    if len(json.dumps(result).encode())>1024*1024:
        result={'status':'response_too_large','reason':'Narrow scope. Execution may have finished; do not replay.'}
    with closing(database()) as db,db:
        db.execute('UPDATE jobs SET status=?,result=?,updated_at=? WHERE id=?',
                   ('finished',json.dumps(result,ensure_ascii=False),now(),operation_id))


def status(operation_id,refresh=True):
    operation_id=str(uuid.UUID(operation_id))
    with closing(database()) as db:
        row=db.execute('SELECT * FROM jobs WHERE id=?',(operation_id,)).fetchone()
    if not row:
        return {'status':'not_found','operation_id':operation_id,'warning':'Not proof that a device has not executed a different request.'}
    value=dict(row)
    result=json.loads(value['result']) if value['result'] else None
    phase=value['status']
    if phase in ('pending','running') and value['pid'] and sys.platform=='linux':
        try:
            if operation_id.encode() not in Path(f"/proc/{value['pid']}/cmdline").read_bytes().split(b'\0'):
                phase='execution_unknown'
        except OSError:
            phase='execution_unknown'
    if phase=='pending' and not value['pid'] and (datetime.now(timezone.utc)-datetime.fromisoformat(value['created_at'])).total_seconds()>30:
        phase='execution_unknown'
    response={'status':phase,'operation_id':operation_id,'operation':value['operation'],
              'created_at':value['created_at'],'checked_at':now(),'result':result}
    if refresh and value['operation'] in ('scale.product.change','scale.text.change') and phase=='finished':
        table='scale_product_change_requests' if value['operation']=='scale.product.change' else 'scale_text_change_requests'
        try:
            rows=rest(table,{'client_request_id':'eq.'+operation_id,'select':'*','limit':2})
            response['executor_requests']=safe_request(rows)
            response['warning']='Executor row, applied verification and app snapshot are separate. Do not infer applied from accepted.'
        except Exception:
            response['executor_status']='unavailable'
    return response


def worker(operation_id):
    global CURRENT_JOB
    CURRENT_JOB=operation_id
    os.umask(0o077)
    with closing(database()) as db,db:
        changed=db.execute("UPDATE jobs SET status='running',updated_at=? WHERE id=? AND status='pending'",(now(),operation_id)).rowcount
        row=db.execute('SELECT * FROM jobs WHERE id=?',(operation_id,)).fetchone()
    if not changed:
        return
    try:
        result=run_action(row['operation'],json.loads(row['parameters']),operation_id)
    except Exception as error:
        result={'status':'execution_unknown' if SPECS[row['operation']][2]!='read' else 'unavailable',
                'error_category':type(error).__name__,
                'reason':'Owning executor failed or response is unconfirmed. Inspect original operation; never retry under a new ID.'}
        allowed={'native_command_failed','native_month_read_failed','invalid_source_response',
                 'receipt_identity_invalid','configured_service_environment_required',
                 'caspi_remote_no_receipt','caspi_remote_receipt_invalid','caspi_text_result_not_verified'}
        if str(error) in allowed:
            result['error_code']=str(error)
    finish(operation_id,result)
    record_job(row,operation_id,result)


def record_job(row,operation_id,result):
    """Existing append contract + delivery queue; logging never retries the business action."""
    try:
        stamp=now()
        event=dict(event_id='mcp-result:'+operation_id,source='waterbe',kind='result',
                   result='observed',feature='mcp.'+row['operation'],target=row['operation'],
                   operation_id=operation_id,observed_at=stamp,route='mcp-native',
                   rule_version='2026.10.21.2',evidence_ids=['waterbe-mcp/action:'+operation_id],
                   changes=[dict(field='status',before='requested',after=result.get('status','observed'))])
        run_action('history.append',{'event':event},operation_id)
    except Exception:
        # Persisted local job is still evidence. Do not mark cloud publication as complete.
        with closing(database()) as db,db:
            value=json.loads(db.execute('SELECT result FROM jobs WHERE id=?',(operation_id,)).fetchone()[0])
            value['history_delivery']='unconfirmed; local action evidence retained'
            db.execute('UPDATE jobs SET result=? WHERE id=?',(json.dumps(value,ensure_ascii=False),operation_id))


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--job':
        worker(str(uuid.UUID(sys.argv[2])))
