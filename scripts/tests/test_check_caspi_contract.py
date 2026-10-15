import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('contract_check',
    Path(__file__).resolve().parents[1] / 'check_caspi_contract.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ContractCheckTests(unittest.TestCase):
    def test_equal_json_and_changed_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cas = root / 'cas'
            app = root / 'app'
            canonical = cas / 'contracts/caspi-v1.json'
            mirror = app / 'test/fixtures/caspi-v1.json'
            canonical.parent.mkdir(parents=True)
            mirror.parent.mkdir(parents=True)
            value = {'protocol_version': 1, 'contract_revision': 1}
            canonical.write_text(json.dumps(value), encoding='utf-8')
            mirror.write_text(json.dumps(value, indent=2), encoding='utf-8')
            self.assertEqual('matched', module.check(cas, app)['status'])
            mirror.write_text(json.dumps({**value, 'contract_revision': 2}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'fixture_mismatch'):
                module.check(cas, app)

    def test_missing_files_are_not_compliant(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                module.check(directory, directory)
