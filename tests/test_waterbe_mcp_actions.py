import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import waterbe_mcp_actions as actions


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.state=patch.object(actions,'STATE',Path(self.temp.name))
        self.state.start()
        self.addCleanup(self.state.stop)
        self.addCleanup(self.temp.cleanup)

    def test_plan_never_executes(self):
        with patch.object(actions,'run_action') as run:
            result=actions.prepare('scale.text.change',dict(store='mia',text_type='advertising',
                text_number=2,operation='upsert',expected_presence='value',expected_content='old',requested_content='new'))
        self.assertEqual(result['status'],'ready')
        run.assert_not_called()

    def test_reject_shell_paths_stores_and_unexpected_fields(self):
        for operation,parameters in [('products.read',{'store':'mia;shutdown'}),
              ('central.restart',{'component':'all'}),('scale.collect',{'store':'mia','shell':'x'}),
              ('recipes.manage',{}),('scale.day.read',{'store':'mia','business_date':'2026-99-99'}),
              ('diagnostics.read',{'store':'mia'}),('sales.daeyoung.sync',{'results_root':'/etc'})]:
            self.assertEqual(actions.prepare(operation,parameters)['status'],'invalid_request')

    def test_write_requires_expectations_and_hash(self):
        payload=dict(store='mia',department=1,plu=15,expected_fields={'normal_price':100},
                     requested_fields={'normal_price':200},base_content_sha256='a'*64)
        self.assertEqual(actions.prepare('scale.product.change',payload)['status'],'ready')
        payload['expected_fields']={}
        self.assertEqual(actions.prepare('scale.product.change',payload)['status'],'invalid_request')

    def test_same_id_does_not_spawn_twice_and_conflict_preserves_original(self):
        key=str(uuid.uuid4())
        with patch.object(actions.subprocess,'Popen') as popen:
            popen.return_value.pid=123
            first=actions.submit('recipes.audit',{},key,'Check recipes')
            second=actions.submit('recipes.audit',{},key,'Check recipes')
            changed=actions.submit('central.check',{},key,'Check central')
        self.assertEqual(popen.call_count,1)
        self.assertEqual(first['operation_id'],second['operation_id'])
        self.assertEqual(changed['status'],'conflict')

    def test_prepared_does_not_imply_user_authority(self):
        with patch.object(actions.subprocess,'Popen') as popen:
            with self.assertRaises(ValueError):
                actions.submit('central.restart',{'component':'history'},str(uuid.uuid4()),'')
            popen.assert_not_called()

    def test_worker_claim_is_once_and_failure_sanitized(self):
        key=str(uuid.uuid4())
        with patch.object(actions.subprocess,'Popen') as popen:
            popen.return_value.pid=123
            actions.submit('central.restart',{'component':'history'},key,'Restart history')
        with patch.object(actions,'run_action',side_effect=RuntimeError('secret-token')),patch.object(actions,'record_job'):
            actions.worker(key)
            actions.worker(key)
        result=actions.status(key)
        self.assertEqual(result['result']['status'],'execution_unknown')
        self.assertNotIn('secret-token',json.dumps(result))

    def test_native_queue_receives_same_id_and_expected_values(self):
        key=str(uuid.uuid4())
        payload=dict(store='mia',department=1,plu=15,expected_fields={'normal_price':100},
                     requested_fields={'normal_price':200},base_content_sha256='a'*64)
        with patch.object(actions,'rest',return_value={'id':key,'status':'pending','last_error':'private-error'}) as rest:
            result=actions.run_action('scale.product.change',payload,key)
        self.assertEqual(rest.call_args.kwargs['payload']['p_client_request_id'],key)
        self.assertEqual(result['status'],'accepted')
        self.assertNotIn('last_error',result['request'])

    def test_bounded_source_page(self):
        with patch.object(actions,'rest',return_value=[{'id':1},{'id':2},{'id':3}]) as rest:
            result=actions.run_action('products.read',{'store':'mia','limit':2},str(uuid.uuid4()))
        self.assertTrue(result['has_more'])
        self.assertEqual(result['next_offset'],2)
        self.assertEqual(rest.call_args.args[0],'products_mia')

    def test_publication_failure_keeps_original_receipt(self):
        key=str(uuid.uuid4())
        receipt=dict(operation_id=key,store_id='mia2',command='aggregate_day',status='succeeded')
        native=SimpleNamespace(load_config=lambda _:dict(stores=[dict(enabled=True,app_store_id='mia',
            controller_store_id='mia2',ssh_alias='mia2')],ssh_timeout_seconds=40),
            execute=lambda *args:receipt)
        with patch.dict(sys.modules,{'caspi_remote_read_worker':native,
                   'caspi_receipt_sync':SimpleNamespace(_envelope=lambda *args:{'receipt':receipt})}), \
             patch.object(actions,'rest',side_effect=OSError('private-error')):
            result=actions.caspi('scale.day.read',dict(store='mia',business_date='2026-10-20'),key)
        self.assertEqual(result['status'],'publication_unconfirmed')
        self.assertEqual(result['receipt'],receipt)

    def test_operation_status_uses_original_id_without_replaying_or_publishing(self):
        key,target=str(uuid.uuid4()),str(uuid.uuid4())
        requests=[]
        def execute(alias,request,timeout):
            requests.append(request)
            return dict(operation_id=target,store_id='mia2',command='write_plu',status='succeeded')
        native=SimpleNamespace(load_config=lambda _:dict(stores=[dict(enabled=True,app_store_id='mia',
            controller_store_id='mia2',ssh_alias='mia2')],ssh_timeout_seconds=40),execute=execute)
        with patch.dict(sys.modules,{'caspi_remote_read_worker':native,
                'caspi_receipt_sync':SimpleNamespace(_envelope=lambda *args:None)}),patch.object(actions,'rest') as publish:
            result=actions.caspi('scale.operation.read',dict(store='mia',target_operation_id=target),key)
        self.assertEqual(requests[0]['command'],'operation_status')
        self.assertEqual(requests[0]['operation_id'],target)
        self.assertEqual(result['status'],'succeeded')
        publish.assert_not_called()


if __name__=='__main__':
    unittest.main()
