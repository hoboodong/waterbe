"""Compare preserved Windows sales rows against the ThinkPad ledger, read-only."""
import argparse
import json
import sqlite3

parser = argparse.ArgumentParser()
parser.add_argument('current')
parser.add_argument('reserve')
args = parser.parse_args()
from pathlib import Path
with sqlite3.connect(Path(args.current).resolve().as_uri() + '?mode=ro', uri=True) as db:
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    db.execute('ATTACH DATABASE ? AS reserve', (Path(args.reserve).resolve().as_uri() + '?mode=ro',))
    assert db.execute('PRAGMA reserve.integrity_check').fetchone()[0] == 'ok'
    columns = 'source_file_id,row_number,sale_date,store,product,daily_qty,daily_sales,month_qty,month_sales,is_store_total'
    missing = db.execute(f'SELECT count(*) FROM (SELECT {columns} FROM reserve.sales_rows EXCEPT SELECT {columns} FROM main.sales_rows)').fetchone()[0]
    missing_sources = db.execute('SELECT count(*) FROM (SELECT file_id,sale_date FROM reserve.source_files EXCEPT SELECT file_id,sale_date FROM main.source_files)').fetchone()[0]
    result = {'windows_rows_not_identical': missing, 'windows_sources_missing': missing_sources}
    result['source_versions'] = [dict(zip(('sale_date','current_modified','reserve_modified'), row)) for row in
        db.execute('SELECT w.sale_date,m.modified_time,w.modified_time FROM reserve.source_files w JOIN main.source_files m ON m.file_id=w.file_id WHERE coalesce(m.modified_time,\'\')<>coalesce(w.modified_time,\'\')')]
    for prefix in ('main', 'reserve'):
        result[prefix] = dict(zip(('rows', 'first_date', 'last_date'), db.execute(f'SELECT count(*),min(sale_date),max(sale_date) FROM {prefix}.sales_rows').fetchone()))
    print(json.dumps(result))
raise SystemExit(2 if missing or missing_sources else 0)
