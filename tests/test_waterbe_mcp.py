import asyncio
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import waterbe_mcp as server
import waterbe_api as api


class McpTests(unittest.TestCase):
    def test_guides_are_curated_and_complete(self):
        paths = server.guide_paths()
        self.assertIn('docs/guides/WATERBE_MCP_GUIDE.md',paths)
        self.assertIn('AGENTS.md',paths)
        self.assertTrue(all((ROOT/p).is_file() for p in paths))
        first = server.waterbe_read_guide('docs/guides/WATERBE_MCP_GUIDE.md',max_lines=2)
        second = server.waterbe_read_guide(first['path'],start_line=first['next_line'],max_lines=2)
        self.assertTrue(first['has_more'])
        self.assertEqual(first['sha256'],second['sha256'])

    def test_arbitrary_files_and_encoded_traversal_are_rejected(self):
        for path in ['../secret.md','config/api_catalog.json','/etc/passwd',
                     '%2e%2e%2fsecret.md','docs/guides/../../.env']:
            with self.assertRaises(ValueError):
                server.guide_info(path)

    def test_catalog_native_and_planned_are_discoverable_not_executable(self):
        entries = server.operations()
        self.assertEqual({e['id'] for e in entries if e['mcp_callable']}, server.READS | server.actions.SPECS.keys())
        with patch.object(api,'call') as call:
            for name in ['scale.product.change','scale.collect','history.append',
                         'sales.namseon.sync','recipes.manage','anything; shell']:
                self.assertEqual(server.execute(name)['status'],'unsupported')
            call.assert_not_called()

    def test_read_requires_date_or_target_and_bounded_inputs(self):
        with patch.object(api,'call') as call:
            for kwargs in [dict(operation='history.read'),
                           dict(operation='sales.namseon.read'),
                           dict(operation='history.read',business_date='2026-99-99'),
                           dict(operation='history.read',operation_id='a',limit=501),
                           dict(operation='history.status',store='x\nsecret')]:
                self.assertEqual(server.execute(**kwargs)['status'],'invalid_request')
            call.assert_not_called()

    def test_failures_and_missing_are_not_zero_or_success(self):
        with patch.object(api,'call',return_value={'status':'missing_source','data':{'rows':[]}}):
            self.assertEqual(server.execute('sales.daeyoung.read','2026-10-21')['status'],'missing_source')
        with patch.object(api,'call',side_effect=OSError('secret-do-not-expose')):
            value=server.execute('history.status')
        self.assertEqual(value['status'],'unavailable')
        self.assertNotIn('secret-do-not-expose',json.dumps(value))

    def test_history_query_is_one_bounded_cursor_page(self):
        data=[{'sequence':n,'body':{}} for n in range(11,14)]
        with patch.dict(os.environ,{'SUPABASE_URL':'https://example.test',
                                  'SUPABASE_SERVICE_ROLE_KEY':'secret'},clear=True), \
             patch.object(api,'urlopen',return_value=io.BytesIO(json.dumps(data).encode())) as request:
            result=server.execute('history.read','2026-10-21',store='mia',after=10,limit=2)
        self.assertEqual(len(result['data']),2)
        self.assertTrue(result['has_more'])
        self.assertEqual(result['next_after'],12)
        self.assertEqual(request.call_count,1)
        from urllib.parse import urlparse,parse_qs
        query=parse_qs(urlparse(request.call_args.args[0].full_url).query)
        self.assertEqual(query['limit'],['3'])
        self.assertEqual(query['sequence'],['gt.10'])
        self.assertIn('guide_sha256',result)

    def test_local_central_does_not_ssh_to_itself(self):
        import system_check
        with patch.dict(os.environ,{'WATERBE_CENTRAL_LOCAL':'1'}), \
             patch.object(system_check,'local_central',return_value={'local':True}), \
             patch.object(system_check,'execute') as remote:
            result=system_check.remote_central()
        self.assertEqual(result['route'],'local_central')
        remote.assert_not_called()

    def test_sdk_handshake_tools_resources_and_prompt(self):
        from mcp import Client
        async def verify():
            async with Client(server.mcp) as client:
                tools=await client.list_tools()
                self.assertEqual(len(tools.tools),10)
                self.assertEqual([t.name for t in tools.tools if not t.annotations.read_only_hint],['waterbe_submit_action'])
                resources=await client.list_resources()
                self.assertEqual(len(resources.resources),3)
                prompts=await client.list_prompts()
                self.assertEqual([p.name for p in prompts.prompts],['waterbe_task'])
                result=await client.call_tool('waterbe_start',{})
                self.assertFalse(result.is_error)
                guide=await client.call_tool('waterbe_read_guide',{'path':'WATERBE_GUIDE.md','max_lines':3})
                self.assertFalse(guide.is_error)
                document=await client.read_resource('waterbe://guide/docs%2Fguides%2FWATERBE_MCP_GUIDE.md')
                self.assertIn('워터비 MCP',document.contents[0].text)
                refused=await client.call_tool('waterbe_call',{'operation':'scale.product.change'})
                self.assertEqual(refused.structured_content['status'],'unsupported')
        asyncio.run(verify())


if __name__=='__main__':
    unittest.main()
