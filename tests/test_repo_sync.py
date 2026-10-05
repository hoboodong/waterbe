import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('repo_sync', Path(__file__).resolve().parents[1] / 'scripts/repo_sync.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class SyncTests(unittest.TestCase):
    def test_current_dirty_tree_is_preserved(self):
        with patch.object(sync, 'git', side_effect=['a', 'main', '', 'a', ' M file', 'a']):
            self.assertEqual(sync.synchronize(Path('.'))['status'], 'up_to_date')

    def test_behind_dirty_tree_is_not_overwritten(self):
        with patch.object(sync, 'git', side_effect=['a', 'main', '', 'b', ' M file', '0 1', 'a']) as git:
            self.assertEqual(sync.synchronize(Path('.'))['status'], 'local_edits_preserved')
            self.assertFalse(any('merge' in call.args for call in git.call_args_list))

    def test_clean_fast_forward(self):
        with patch.object(sync, 'git', side_effect=['a', 'main', '', 'b', '', '0 1', '', 'b']):
            self.assertEqual(sync.synchronize(Path('.'))['status'], 'updated')

    def test_divergence_is_not_reset(self):
        with patch.object(sync, 'git', side_effect=['a', 'main', '', 'b', '', '1 1', 'a']):
            self.assertEqual(sync.synchronize(Path('.'))['status'], 'diverged')


if __name__ == '__main__':
    unittest.main()
