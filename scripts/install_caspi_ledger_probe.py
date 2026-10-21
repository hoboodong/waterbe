"""Narrow CASPi initialization patch; no database rewrite, service restart or scale write.

Run on an authorized Pi via sudo python3 after testing the same source change.
Only the exact old backfill block is replaced; all other installed bytes remain.
"""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import argparse

OLD='''        self.connection.execute(
            """INSERT OR IGNORE INTO receipt_event(operation_id,request_json,receipt_json,completed_at)
            SELECT operation_id,request_json,receipt_json,completed_at FROM operation
            WHERE receipt_json IS NOT NULL AND completed_at IS NOT NULL
            ORDER BY completed_at,operation_id""")'''
NEW='''        # Probe identifiers through indexes before touching large receipt bodies.
        # The previous unconditional INSERT scanned/copies every saved receipt and
        # requested a write lock on every CLI/feed connection, even with no gap.
        missing = """SELECT operation_id FROM operation
                     EXCEPT SELECT operation_id FROM receipt_event"""
        eligible = f"""SELECT operation_id FROM operation
                       WHERE operation_id IN ({missing})
                         AND receipt_json IS NOT NULL AND completed_at IS NOT NULL"""
        if self.connection.execute(eligible + " LIMIT 1").fetchone():
            self.connection.execute(
                f"""INSERT OR IGNORE INTO receipt_event(operation_id,request_json,receipt_json,completed_at)
                SELECT operation_id,request_json,receipt_json,completed_at FROM operation
                WHERE operation_id IN ({eligible})
                ORDER BY completed_at,operation_id""")'''


def patch_source(source):
    if NEW in source:
        return source
    if source.count(OLD)!=1:
        raise ValueError('installed_source_does_not_match_reviewed_block')
    updated=source.replace(OLD,NEW,1)
    compile(updated,'caspi_bluetooth.py','exec')
    return updated


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--central-source',action='store_true',help='Patch canonical CAS source only, preserving unrelated edits')
    args=parser.parse_args()
    os.umask(0o077)
    path=(Path.home()/'cascl5200/scale-data/tools/caspi_bluetooth.py' if args.central_source
          else Path('/opt/caspi/caspi_bluetooth.py')).resolve(strict=True)
    original=path.read_bytes()
    updated=patch_source(original.decode('utf-8')).encode('utf-8')
    if original==updated:
        print(json.dumps({'status':'already_installed','sha256':hashlib.sha256(original).hexdigest()}))
        return
    base=Path.home()/'.local/state/waterbe-mcp/cas-source-backups' if args.central_source else Path('/var/backups/caspi-ledger-probe')
    evidence=base/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    evidence.mkdir(parents=True,mode=0o700)
    shutil.copy2(path,evidence/'caspi_bluetooth.py')
    staging=path.with_name('caspi_bluetooth.py.mcp-new')
    staging.write_bytes(updated)
    shutil.copymode(path,staging)
    os.replace(staging,path)
    result=dict(status='installed',before_sha256=hashlib.sha256(original).hexdigest(),
                after_sha256=hashlib.sha256(updated).hexdigest(),backup=str(evidence),
                database_rewritten=False,services_restarted=False,business_writes=0)
    (evidence/'installation.json').write_text(json.dumps(result)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    main()
