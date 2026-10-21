from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from install_caspi_ledger_probe import OLD,NEW,patch_source


class PatchTests(unittest.TestCase):
    def test_exact_source_only_and_idempotence(self):
        source='def initialize(self):\n'+OLD+'\n'
        updated=patch_source(source)
        self.assertEqual(updated,'def initialize(self):\n'+NEW+'\n')
        self.assertEqual(patch_source(updated),updated)

    def test_unrecognized_source_is_not_overwritten(self):
        with self.assertRaises(ValueError):
            patch_source('def initialize(self):\n    pass\n')


if __name__=='__main__':
    unittest.main()
