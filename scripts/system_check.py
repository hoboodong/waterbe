"""One read-only inspection entry: direct Supabase + remote central/CASPi evidence.

No restart, collection, scale command, credential copying, or business mutation.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

PROJECT = 'uvlmxspvgaagqaisdvhj'
STORES = ('mapo2','mia2','wolgye2','wangsim2','mooner2')
SQL = """SELECT jsonb_build_object(
 'checked_at',now(),
 'connections',(SELECT count(*) FROM pg_stat_activity),
 'active_queries',(SELECT count(*) FROM pg_stat_activity WHERE state='active' AND pid<>pg_backend_pid()),
 'waiting_locks',(SELECT count(*) FROM pg_locks WHERE NOT granted),
 'oldest_active_seconds',(SELECT coalesce(max(extract(epoch FROM now()-query_start)),0) FROM pg_stat_activity WHERE state='active' AND pid<>pg_backend_pid()),
 'database_bytes',pg_database_size(current_database())) AS evidence"""

PI_CODE = """import json,pathlib,sqlite3,subprocess,datetime
c=json.loads(pathlib.Path('/etc/caspi/caspi.json').read_text())
services={}
for name in ('caspi.service',):
 p=subprocess.run(['systemctl','show',name,'-p','ActiveState','-p','ExecMainStatus'],capture_output=True,text=True,timeout=5)
 services[name]=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
path=pathlib.Path(c['aggregate_database_path']).resolve()
d=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=3)
d.row_factory=sqlite3.Row
tables={r[0] for r in d.execute("SELECT name FROM sqlite_master WHERE type='table'")}
observation=[]
if 'observation_state' in tables:
 allowed={'checked_at','collection_id','store_id','observed_at','collected_at','last_success_at','last_attempt_at','status','failure_code','consecutive_failures','updated_at'}
 observation=[{k:r[k] for k in r.keys() if k in allowed} for r in d.execute('SELECT * FROM observation_state ORDER BY rowid DESC LIMIT 5')]
print(json.dumps({'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'store_id':c.get('store_id'),'services':services,'observation':observation,'database_mtime':datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat(),'physical_scale_verified':False}))
"""


def stamp():
    return datetime.now(timezone.utc).isoformat()


def execute(args, timeout, input_text=None):
    started = time.monotonic()
    try:
        process = subprocess.run(args,input=input_text,text=True,encoding='utf-8',
                                 capture_output=True,timeout=timeout)
        if process.returncode:
            return {'status':'unavailable','reason':'command_failed','exit_code':process.returncode,
                    'checked_at':stamp()}, None
        data = json.loads(process.stdout)
        return {'status':'available','checked_at':stamp(),
                'elapsed_seconds':round(time.monotonic()-started,3)}, data
    except subprocess.TimeoutExpired:
        reason = 'timeout'
    except FileNotFoundError:
        reason = 'tool_missing'
    except (ValueError, OSError):
        reason = 'invalid_or_unavailable_response'
    return {'status':'unavailable','reason':reason,'checked_at':stamp()}, None


def find_cli():
    explicit = os.environ.get('WATERBE_SUPABASE_CLI')
    if explicit:
        return explicit
    found = shutil.which('supabase')
    if found:
        return found
    local = Path(os.environ.get('LOCALAPPDATA',''))/'Programs/SupabaseCLI/bin/supabase.exe'
    return str(local) if local.is_file() else 'supabase'


def direct_supabase():
    cli = find_cli()
    platform, projects = execute([cli,'projects','list','-o','json'],20)
    if isinstance(projects,list):
        project = next((p for p in projects if p.get('id',p.get('ref'))==PROJECT),None)
        if project:
            platform['project_status'] = project.get('status')
        else:
            platform.update(status='unavailable',reason='project_not_accessible')
    elif projects is not None:
        platform.update(status='unavailable',reason='invalid_project_response')
    database, rows = execute([cli,'db','query','--linked','--project-ref',PROJECT,SQL,'-o','json'],25)
    if rows is not None:
        try:
            if isinstance(rows,dict):
                rows=rows.get('rows')
            if not isinstance(rows,list) or len(rows)!=1:
                raise ValueError()
            evidence = rows[0]['evidence']
            if isinstance(evidence,str):
                evidence=json.loads(evidence)
            allowed=('checked_at','connections','active_queries','waiting_locks','oldest_active_seconds','database_bytes')
            database['evidence']={k:evidence[k] for k in allowed}
        except (KeyError,TypeError,ValueError):
            database.update(status='unavailable',reason='invalid_db_response')
    return {'route':'local_direct_supabase_cli','platform':platform,'database':database,
            'app_rest_verified':False,'io_budget_verified':False}


def inspect_pi(alias):
    meta, evidence = execute(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=6',alias,
                              'sudo','-n','python3','-'],20,PI_CODE)
    if isinstance(evidence,dict):
        for row in evidence.get('observation',[]):
            try:
                age=(datetime.now(timezone.utc)-datetime.fromisoformat(row['checked_at'].replace('Z','+00:00'))).total_seconds()
                row['age_seconds']=round(age)
                row['freshness']='stale' if age>180 or age<0 else 'recent'
            except (KeyError,ValueError,TypeError):
                row['freshness']='unverified'
    return {'device':alias,**meta,'evidence':evidence}


def local_central():
    home=Path.home()
    manager, data=execute([str(home/'.local/bin/waterbe-central'),'manage','check'],35)
    # Known manager projection only. Never return arbitrary stdout/logs.
    components={}
    if isinstance(data,dict) and isinstance(data.get('components'),dict):
        for key,value in data['components'].items():
            allowed=('Id','ActiveState','SubState','ExecMainStatus','LastTriggerUSec','ActiveEnterTimestamp')
            components[key]={k:value.get(k) for k in allowed if k in value}
            if isinstance(value.get('last_run'),dict):
                components[key]['last_run']={k:value['last_run'].get(k) for k in
                                             ('ActiveState','ExecMainStatus','ExecMainExitTimestamp')}
    elif manager['status']=='available':
        manager.update(status='unavailable',reason='invalid_manager_response')
    history={'status':'unavailable','reason':'history_unreadable','checked_at':stamp()}
    try:
        db_path=home/'.local/state/waterbe-history/operations.db'
        with sqlite3.connect(db_path.as_uri()+'?mode=ro',uri=True,timeout=3) as db:
            db.row_factory=sqlite3.Row
            coverage=[dict(r) for r in db.execute('SELECT source,checked_at,success_at,status FROM coverage')]
            now=datetime.now(timezone.utc)
            for row in coverage:
                age=(now-datetime.fromisoformat(row['checked_at'].replace('Z','+00:00'))).total_seconds()
                row['age_seconds']=round(age)
                row['freshness']='stale' if age>1200 or age<0 else 'recent'
            history={'status':'available','checked_at':stamp(),'coverage':coverage,
                     'pending':db.execute('SELECT count(*) FROM delivery WHERE delivered_at IS NULL').fetchone()[0],
                     'quarantined':db.execute('SELECT count(*) FROM quarantine').fetchone()[0]}
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'source_failure_evidence' in tables:
                history['recent_failures']=[dict(r) for r in db.execute('SELECT source,checked_at,category,http_status FROM source_failure_evidence ORDER BY checked_at DESC LIMIT 20')]
    except (sqlite3.Error,OSError,ValueError):
        pass
    with ThreadPoolExecutor(max_workers=5) as pool:
        devices=list(pool.map(inspect_pi,STORES))
    return {'checked_at':stamp(),'manager':{**manager,'components':components},
            'history':history,'devices':devices}


def remote_central():
    if os.environ.get('WATERBE_CENTRAL_LOCAL') == '1':
        return {'route':'local_central',
                'connection':{'status':'available','checked_at':stamp()},
                'data':local_central()}
    # Execute exact version over stdin; no upload or persistent remote installation.
    meta, data=execute(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','thinkpad',
                        'python3','-','--remote-central'],60,Path(__file__).read_text(encoding='utf-8'))
    return {'route':'ssh_thinkpad','connection':meta,'data':data}


def assessment(supabase, thinkpad):
    issues=[]
    for name in ('platform','database'):
        if supabase[name]['status']!='available':
            issues.append({'target':'supabase.'+name,'state':'unverified','reason':supabase[name].get('reason')})
    if supabase['platform'].get('project_status') not in (None,'ACTIVE_HEALTHY'):
        issues.append({'target':'supabase.platform','state':'requires_review'})
    data=thinkpad.get('data') or {}
    for name, component in data.get('manager',{}).get('components',{}).items():
        if component.get('ActiveState')=='failed':
            issues.append({'target':'central.'+name,'state':'failed'})
        last=component.get('last_run',{})
        if last.get('ActiveState')!='activating' and last.get('ExecMainStatus') not in (None,'0'):
            issues.append({'target':'central.'+name,'state':'last_run_failed',
                           'checked_at':last.get('ExecMainExitTimestamp')})
    history=data.get('history',{})
    for row in history.get('coverage',[]):
        if row.get('status')!='available' or row.get('freshness')=='stale':
            issues.append({'target':row['source'],'state':row.get('freshness') if row.get('freshness')=='stale' else row.get('status'),
                           'checked_at':row.get('checked_at')})
    for row in data.get('devices',[]):
        if row['status']!='available':
            issues.append({'target':row['device'],'state':'unverified','reason':row.get('reason')})
        else:
            if row.get('evidence',{}).get('services',{}).get('caspi.service',{}).get('ActiveState')!='active':
                issues.append({'target':row['device']+'.caspi','state':'requires_review'})
            observations=row.get('evidence',{}).get('observation',[])
            if not observations or any(o.get('freshness') in ('stale','unverified') for o in observations):
                issues.append({'target':row['device']+'.aggregate_observation','state':'stale_or_unverified'})
    return issues


def check():
    with ThreadPoolExecutor(max_workers=2) as pool:
        cloud=pool.submit(direct_supabase)
        central=pool.submit(remote_central)
        supabase,thinkpad=cloud.result(),central.result()
    data=thinkpad.get('data') or {}
    required=[supabase['platform']['status'],supabase['database']['status'],thinkpad['connection']['status'],
              data.get('manager',{}).get('status','unavailable'),data.get('history',{}).get('status','unavailable')]
    required.extend(r['status'] for r in data.get('devices',[]))
    return {'operation':'system.check','checked_at':stamp(),
            'status':'available' if all(s=='available' for s in required) else 'partial',
            'supabase':supabase,'central':thinkpad,
            'issues':assessment(supabase,thinkpad),
            'limitations':['available means evidence retrieval, not all systems healthy',
                           'No phone/Bluetooth or physical scale command verification',
                           'No automatic repair/restart; no business data mutation']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote-central',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    result=local_central() if args.remote_central else check()
    print(json.dumps(result,ensure_ascii=False))
    return 0 if args.remote_central or result['status']=='available' else 1


if __name__=='__main__':
    raise SystemExit(main())
