"""Read-only evidence for the ThinkPad CASPi adaptive aggregate deployment."""
from contextlib import closing
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import uuid


def inspect(path):
    now = datetime.now(timezone.utc)
    result = {'checked_at':now.isoformat(),'stores':{}}
    with closing(sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT * FROM store_observation ORDER BY store_id'):
            item = dict(row)
            checked = item.get('checked_at')
            item['physical_read_age_seconds'] = round((now-datetime.fromisoformat(checked)).total_seconds(),1) if checked else None
            result['stores'][row['store_id']] = item
        result['latest_import'] = dict(db.execute('SELECT * FROM sync_run ORDER BY id DESC LIMIT 1').fetchone())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--record',action='store_true')
    args = parser.parse_args()
    proof = inspect(Path.home()/'.local/state/cas-central/aggregate-central.sqlite3')
    if args.manifest:
        expected = json.loads(args.manifest.read_text())
        proof['installed_hashes'] = {}
        for store in ('mapo2','mia2','mooner2','wolgye2','wangsim2'):
            files = ['/opt/caspi/'+name for name in expected]
            response = subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',store,
                'sudo','-n','sha256sum',*files],capture_output=True,text=True,timeout=20,check=True)
            actual = {Path(line.split(maxsplit=1)[1]).name:line.split()[0] for line in response.stdout.splitlines()}
            if actual != expected:
                raise RuntimeError('installed_hash_mismatch:'+store)
            proof['installed_hashes'][store] = actual
        proof['manifest_sha256'] = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    if args.record:
        if not args.manifest:
            parser.error('record requires verified installation manifest')
        import sys
        sys.path.insert(0,str(Path.home()/'waterbe/scripts'))
        import central_manage
        operation = 'caspi-adaptive-'+str(uuid.uuid4())
        proof['operation_id'] = operation
        proof['physical_collection_complete'] = all(row['last_attempt_status']=='succeeded' for row in proof['stores'].values())
        root = Path.home()/'.local/state/waterbe-history/manager-evidence'
        root.mkdir(parents=True,exist_ok=True,mode=0o700)
        path = root/(operation+'.json')
        path.write_text(json.dumps(proof,ensure_ascii=False),encoding='utf-8')
        path.chmod(0o600)
        central_manage.record(root.parent/'operations.db',operation,'aggregate','result','succeeded',
            'central-manager:'+operation)
    print(json.dumps(proof,ensure_ascii=False))
