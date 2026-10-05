import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import history_worker as worker
import operation_history as history


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'history.db'
        worker.initialize(self.db)
        self.source = worker.sources()[0]
        self.rows = [dict(id='p1', name='새우', retail_price=100, mart_code='123', is_operating=True)]
        self.now = '2026-10-05T01:00:00.000000+00:00'

    def test_baseline_change_and_replay(self):
        self.assertEqual(worker.ingest(self.db,self.source,self.rows,self.now),1)
        self.assertEqual(worker.ingest(self.db,self.source,self.rows,self.now),0)
        changed = [{**self.rows[0], 'retail_price': 200}]
        worker.ingest(self.db,self.source,changed,'2026-10-05T02:00:00.000000+00:00')
        events = history.query(self.db)['events']
        self.assertEqual(events[0]['kind'],'observation')
        self.assertEqual(events[1]['changes'],[dict(field='price',before=100,after=200)])
        self.assertNotIn('occurred_at',events[1])

    def test_polling_skips_recent_products_without_refreshing_coverage(self):
        previous = {'success_at': self.now, 'status': 'available'}
        self.assertEqual(worker.polling_plan(self.source,previous,self.now,
                         '2026-10-05T01:01:00+00:00'), (False,None))

    def test_incremental_crosses_midnight(self):
        entry = next(e for e in worker.sources() if e['table'].startswith('print_records_'))
        previous = {'success_at':'2026-10-05T23:59:00+00:00','status':'available'}
        due, since = worker.polling_plan(entry,previous,previous['success_at'],
                                        '2026-10-06T00:01:00+00:00')
        self.assertTrue(due)
        self.assertEqual(since,'2026-10-05T23:49:00+00:00')

    def test_failed_source_is_retried_and_full_scan_is_bounded(self):
        previous = {'success_at':self.now,'status':'unavailable'}
        due, since = worker.polling_plan(self.source,previous,self.now,'2026-10-05T01:01:00+00:00')
        self.assertTrue(due)
        self.assertIsNotNone(since)
        self.assertEqual(worker.polling_plan(self.source,previous,self.now,
                         '2026-10-06T01:01:00+00:00'), (True,None))

    def test_bad_record_does_not_stop_next(self):
        self.assertEqual(worker.ingest(self.db,self.source,[dict(id=None)]+self.rows,self.now),1)
        self.assertEqual(worker.status(self.db)['quarantined'],1)

    def test_delivery_retry_is_same_event(self):
        worker.ingest(self.db,self.source,self.rows,self.now)
        with patch.object(worker,'rest',side_effect=OSError('network')):
            self.assertEqual(worker.deliver(self.db),0)
        self.assertEqual(worker.status(self.db)['pending'],1)
        event=history.query(self.db)['events'][0]
        with patch.object(worker,'rest',return_value=[{'status':'duplicate','event_id':event['event_id'],'source':event['source']}]):
            self.assertEqual(worker.deliver(self.db),1)
        self.assertEqual(worker.status(self.db)['pending'],0)
        self.assertEqual(len(history.query(self.db)['events']),1)

    def test_source_projections_exclude_payload(self):
        for source in worker.sources():
            self.assertNotIn('print_payload',source['fields'])
            self.assertNotIn('drive_url',source['fields'])
            self.assertNotIn('operation',source['fields'])

    def test_backup_can_be_read(self):
        worker.ingest(self.db,self.source,self.rows,self.now)
        worker.backup(self.db)
        backups=list(Path(self.temp.name).glob('backups/*/operations.db'))
        self.assertEqual(len(backups),1)
        self.assertEqual(len(history.query(backups[0])['events']),1)

    def test_new_monitored_field_is_not_claimed_as_change(self):
        worker.ingest(self.db,self.source,self.rows,self.now)
        entry={**self.source,'fields':{**self.source['fields'],'new':'cost'}}
        worker.ingest(self.db,entry,[{**self.rows[0],'new':10}],'2026-10-05T02:00:00.000000+00:00')
        self.assertEqual(history.query(self.db)['events'][-1]['kind'],'observation')

    def test_health_notice_isolated_and_recovery(self):
        worker.health_notice(self.db,'products_wangsimni',False,self.now)
        worker.health_notice(self.db,'products_wangsimni',False,self.now)
        worker.health_notice(self.db,'products_wangsimni',False,self.now)
        root=Path(self.temp.name)/'logs'
        worker.publish_notices(self.db,root)
        worker.publish_notices(self.db,root)
        file=list(root.glob('*.jsonl'))[0]
        self.assertEqual(len(file.read_text(encoding='utf-8').splitlines()),1)
        worker.health_notice(self.db,'products_wangsimni',True,'2026-10-05T02:00:00.000000+00:00')
        worker.publish_notices(self.db,root)
        self.assertEqual(len(file.read_text(encoding='utf-8').splitlines()),2)
        self.assertEqual([e['kind'] for e in history.query(self.db)['events']],['incident','recovery'])


if __name__ == '__main__':
    unittest.main()
