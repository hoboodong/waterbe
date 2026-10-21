"""Explicit MCP client smoke check; no model call or business mutation.

Examples: python check_waterbe_mcp.py --ssh thinkpad --live
          python check_waterbe_mcp.py --local --live
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from mcp import Client, StdioServerParameters


async def check(args):
    if args.ssh:
        parameters=StdioServerParameters(command='ssh',args=['-T','-o','BatchMode=yes',
            '-o','ConnectTimeout=8',args.ssh,'/home/sdg/.local/bin/waterbe-mcp'])
    else:
        parameters=StdioServerParameters(command=str(Path.home()/'.local/bin/waterbe-mcp'))
    evidence={'checked_at':datetime.now(timezone.utc).isoformat(),
              'route':'ssh:'+args.ssh if args.ssh else 'central-local','business_mutations':0}
    async with Client(parameters,read_timeout_seconds=180) as client:
        tools=await client.list_tools()
        evidence['tools']=[t.name for t in tools.tools]
        resources=await client.list_resources()
        evidence['resources']=[str(r.uri) for r in resources.resources]
        prompts=await client.list_prompts()
        evidence['prompts']=[p.name for p in prompts.prompts]
        start=await client.call_tool('waterbe_start',{})
        assert not start.is_error
        evidence['source']=start.structured_content['source']
        found=await client.call_tool('waterbe_find_guides',{'query':'저울'})
        assert not found.is_error and found.structured_content['count']>0
        guide=await client.call_tool('waterbe_read_guide',{'path':'docs/guides/WATERBE_MCP_GUIDE.md'})
        assert not guide.is_error
        evidence['guide_sha256']=guide.structured_content['sha256']
        refused=await client.call_tool('waterbe_call',{'operation':'scale.product.change'})
        assert refused.structured_content['status']=='unsupported'
        evidence['unconnected_write_not_executed']=True
        if args.live:
            status=await client.call_tool('waterbe_call',{'operation':'history.status'})
            assert not status.is_error
            data=status.structured_content
            evidence['history_status']=data['status']
            evidence['history_rows']=len(data.get('data') or [])
            if data['status']!='available':
                raise RuntimeError('live_history_query_unavailable')
            page=await client.call_tool('waterbe_call',{
                'operation':'history.read','business_date':'2026-10-20', 'source':'deployment', 'limit':5})
            assert not page.is_error and page.structured_content['status']=='available'
            evidence['history_page_rows']=len(page.structured_content['data'])
            evidence['history_page_has_more']=page.structured_content['has_more']
    print(json.dumps(evidence,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--ssh')
    mode.add_argument('--local',action='store_true')
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    asyncio.run(check(args))


if __name__=='__main__':
    main()
