import sys
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import system_check as monitor


class SystemCheckTests(unittest.TestCase):
    def test_no_raw_failure_or_credentials(self):
        p=subprocess.CompletedProcess([],1,'secret-token','secret-password')
        with patch.object(monitor.subprocess,'run',return_value=p):
            meta,data=monitor.execute(['example'],1)
        self.assertEqual(meta['status'],'unavailable')
        self.assertIsNone(data)
        self.assertNotIn('secret',str(meta))

    def test_timeout_is_explicit(self):
        with patch.object(monitor.subprocess,'run',side_effect=subprocess.TimeoutExpired('x',1)):
            meta,_=monitor.execute(['example'],1)
        self.assertEqual(meta['reason'],'timeout')

    def test_direct_cloud_projection(self):
        meta={'status':'available','checked_at':'now'}
        evidence={'checked_at':'now','connections':10,'active_queries':1,'waiting_locks':0,
                  'oldest_active_seconds':2,'database_bytes':100,'secret':'never'}
        with patch.object(monitor,'execute',side_effect=[(meta.copy(),[{'id':monitor.PROJECT,'status':'ACTIVE_HEALTHY','secret':'never'}]),
                                                         (meta.copy(),{'rows':[{'evidence':evidence}],'warning':'never'})]):
            result=monitor.direct_supabase()
        self.assertEqual(result['platform']['project_status'],'ACTIVE_HEALTHY')
        self.assertNotIn('never',str(result))
        self.assertFalse(result['app_rest_verified'])

    def test_one_failed_path_does_not_hide_other(self):
        cloud={'platform':{'status':'available'},'database':{'status':'available'}}
        central={'connection':{'status':'unavailable'},'data':None}
        with patch.object(monitor,'direct_supabase',return_value=cloud),patch.object(monitor,'remote_central',return_value=central):
            result=monitor.check()
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['supabase'],cloud)

    def test_cloud_failure_keeps_central_evidence(self):
        cloud={'platform':{'status':'unavailable'},'database':{'status':'unavailable'}}
        data={'manager':{'status':'available'},'history':{'status':'available'},
              'devices':[{'device':'mapo2','status':'available',
                          'evidence':{'services':{'caspi.service':{'ActiveState':'active'}}}}]}
        central={'connection':{'status':'available'},'data':data}
        with patch.object(monitor,'direct_supabase',return_value=cloud),patch.object(monitor,'remote_central',return_value=central):
            result=monitor.check()
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['central']['data'],data)

    def test_running_oneshot_does_not_inherit_old_failure(self):
        cloud={'platform':{'status':'available'},'database':{'status':'available'}}
        data={'manager':{'components':{'aggregate':{'ActiveState':'active',
              'last_run':{'ActiveState':'activating','ExecMainStatus':'1'}}}}}
        self.assertEqual(monitor.assessment(cloud,{'data':data}),[])
        data['manager']['components']['aggregate']['last_run']['ActiveState']='failed'
        self.assertEqual(monitor.assessment(cloud,{'data':data})[0]['state'],'last_run_failed')


if __name__=='__main__':
    unittest.main()
