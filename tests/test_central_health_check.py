import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'scripts'))
import central_health_check as checker


class CentralHealthTests(unittest.TestCase):
    def test_running_oneshot_is_unknown_not_previous_failure_or_recovery(self):
        timer = {'LoadState':'loaded','ActiveState':'active'}
        for code in ('0','2'):
            service = {'LoadState':'loaded','ActiveState':'activating','ExecMainStatus':code}
            self.assertIsNone(checker.timed_health(timer,service,{0}))

    def test_completed_result_and_timer_are_checked(self):
        timer = {'LoadState':'loaded','ActiveState':'active'}
        service = {'LoadState':'loaded','ActiveState':'inactive','ExecMainStatus':'0'}
        self.assertTrue(checker.timed_health(timer,service,{0}))
        self.assertFalse(checker.timed_health(timer,{**service,'ExecMainStatus':'2'},{0}))
        self.assertFalse(checker.timed_health({**timer,'ActiveState':'inactive'},service,{0}))
