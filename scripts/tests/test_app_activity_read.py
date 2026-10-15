import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('activity', Path(__file__).resolve().parents[1] / 'app_activity_read.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ActivityTests(unittest.TestCase):
    def test_read_only_filters_and_injection_rejected_before_execution(self):
        calls = []
        def execute(sql):
            calls.append(sql)
            return []
        result = module.read('mia', '2026-10-15', 'products', execute=execute)
        self.assertEqual('available', result['status'])
        self.assertTrue(calls[0].startswith('SELECT '))
        self.assertIn("store_id='mia'", calls[0])
        self.assertIn('received_at<=', calls[0])
        with self.assertRaises(ValueError):
            module.read('mia', '2026-10-15', "products';delete", execute=execute)
        self.assertEqual(1, len(calls))

    def test_pagination_and_limit_do_not_claim_full_coverage(self):
        pages = iter([[{}] * 100, [{}] * 2])
        result = module.read('mia', '2026-10-15', limit=101, execute=lambda _: next(pages))
        self.assertEqual('partial', result['status'])
        self.assertEqual(101, len(result['events']))
