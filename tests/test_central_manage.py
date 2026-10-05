import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('central_manage', SCRIPTS / 'central_manage.py')
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class ManagementTests(unittest.TestCase):
    def test_request_and_result_are_queued(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'history.db'
            manage.record(database, 'test-operation', 'health', 'request', 'pending')
            manage.record(database, 'test-operation', 'health', 'result', 'succeeded', 'proof:test')
            with manage.closing(manage.history.connect(database)) as db:
                self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0], 2)
                self.assertEqual(db.execute('SELECT count(*) FROM delivery').fetchone()[0], 2)

    def test_disabled_unit_is_not_restarted(self):
        with patch.object(manage, 'inspect', return_value={'UnitFileState': 'disabled'}), \
             patch.object(manage, 'run') as command:
            with self.assertRaisesRegex(RuntimeError, 'disabled_unit'):
                manage.restart('health', Path('unused'), SCRIPTS.parent)
            command.assert_not_called()

    def test_supervisor_circuit_is_not_bypassed(self):
        from types import SimpleNamespace
        response = SimpleNamespace(returncode=0, stdout='{"circuit_open":true,"processing":{}}')
        with patch.object(manage, 'run', return_value=response) as command:
            with self.assertRaisesRegex(RuntimeError, 'business_state'):
                manage.restart('supervisor', Path('unused'), SCRIPTS.parent)
            self.assertEqual(command.call_count, 1)

    def test_unknown_component_cannot_form_a_command(self):
        with patch.object(manage, 'run') as command:
            with self.assertRaises(KeyError):
                manage.inspect('unregistered.service')
            command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
