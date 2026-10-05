import importlib.util
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('history', Path(__file__).resolve().parents[1] / 'scripts/operation_history.py')
history = importlib.util.module_from_spec(spec)
spec.loader.exec_module(history)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'events.db'
        self.event = dict(event_id='one', source='caspi', kind='change', result='observed',
                          feature='scale.product', target='34', store='wangsimni',
                          observed_at='2026-10-05T10:00:00+09:00',
                          changes=[dict(field='product_name_5', before='', after='업소명')])

    def test_durable_duplicate_and_conflict(self):
        self.assertEqual(history.append(self.db, self.event)['status'], 'stored')
        self.assertEqual(history.append(self.db, self.event)['status'], 'duplicate')
        changed = {**self.event, 'target': '35'}
        with self.assertRaises(ValueError):
            history.append(self.db, changed)
        self.assertEqual(len(history.query(self.db)['events']), 1)

    def test_read_does_not_create(self):
        self.assertEqual(history.query(self.db)['status'], 'unavailable')
        self.assertFalse(self.db.exists())

    def test_filters_and_pages(self):
        for index in range(3):
            history.append(self.db, {**self.event, 'event_id': str(index)})
        page = history.query(self.db, store='wangsimni', limit=2, since='2026-10-05T00:00:00Z')
        self.assertTrue(page['has_more'])
        self.assertEqual(len(history.query(self.db, after=page['next_after'])['events']), 1)
        self.assertFalse(history.query(self.db, store='mia')['events'])

    def test_append_only(self):
        history.append(self.db, self.event)
        with closing(sqlite3.connect(self.db)) as db, db:
            for sql in ('DELETE FROM events', "UPDATE events SET target='x'"):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)

    def test_invalid_input(self):
        for changes in ({'observed_at': '2026-10-05T10:00:00'},
                        {'token': 'secret'}, {'source': 'unknown'},
                        {'changes': [dict(field='password', before='', after='secret')]},
                        {'result': 'succeeded', 'kind': 'result'},
                        {'evidence_ids': ['https://example.test?token=secret']},
                        {'occurred_at': '2026-10-06T00:00:00Z'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                history.append(self.db, {**self.event, **changes})
        self.assertFalse(self.db.exists())

    def test_late_and_unknown_occurrence(self):
        history.append(self.db, {**self.event, 'last_confirmed_at': '2026-10-01T00:00:00Z'})
        event = history.query(self.db)['events'][0]
        self.assertNotIn('occurred_at', event)
        self.assertEqual(event['observed_at'], '2026-10-05T01:00:00.000000+00:00')

    def test_same_second_precision(self):
        history.append(self.db, self.event)
        self.assertEqual(len(history.query(self.db, since='2026-10-05T01:00:00.000000Z')['events']), 1)
        self.assertFalse(history.query(self.db, since='2026-10-05T01:00:00.000001Z')['events'])


if __name__ == '__main__':
    unittest.main()
