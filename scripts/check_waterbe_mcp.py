"""Explicit MCP client smoke check; no model call or business mutation.

Examples: python check_waterbe_mcp.py --ssh thinkpad --live
          python check_waterbe_mcp.py --local --live
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import uuid
from pathlib import Path

from mcp import Client, StdioServerParameters


async def check(args):
    if args.ssh:
        parameters=StdioServerParameters(command=args.ssh_command,args=['-T','-o','BatchMode=yes',
            '-o','ConnectTimeout=8',args.ssh,'/home/sdg/.local/bin/waterbe-mcp'])
    else:
        parameters=StdioServerParameters(command=str(Path.home()/'.local/bin/waterbe-mcp'))
    evidence={'checked_at':datetime.now(timezone.utc).isoformat(),
              'route':'ssh:'+args.ssh if args.ssh else 'central-local','business_mutations':0}
    async with Client(parameters,read_timeout_seconds=180,mode='legacy') as client:
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
        evidence['read_tool_does_not_execute_writes']=True
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
        if args.native:
            connections=await client.call_tool('waterbe_check_connections',{})
            evidence['connections']=connections.structured_content
            evidence['native_reads']=[]
            for operation,parameters in [
                ('products.read',dict(store=args.store,limit=1)),
                ('discounts.read',dict(store=args.store,business_date=args.business_date,limit=1)),
                ('diagnostics.read',dict(store=args.store,business_date=args.business_date,limit=1)),
                ('scale.products.read',dict(store=args.store,limit=1)),
                ('scale.texts.read',dict(store=args.store,limit=1)),
                ('scale.work.read',dict(store=args.store)),
                ('recipes.audit',{}),('central.check',{}),
                ('scale.day.read',dict(store=args.store,business_date=args.business_date,limit=1)),
            ]:
                operation_id=str(uuid.uuid4())
                await client.call_tool('waterbe_submit_action',dict(operation=operation,
                    parameters=parameters,operation_id=operation_id,
                    user_request='Read-only MCP installation verification; no scale writes'))
                outcome=None
                for _ in range(150):
                    await asyncio.sleep(.4)
                    value=(await client.call_tool('waterbe_action_status',{'operation_id':operation_id})).structured_content
                    if value['status'] not in ('pending','running'):
                        outcome=value
                        break
                result=(outcome or {}).get('result') or {}
                evidence['native_reads'].append(dict(operation=operation,operation_id=operation_id,
                    job_status=(outcome or {}).get('status','timeout_waiting'),
                    result_status=result.get('status','read_returned' if result else 'unavailable'),
                    error_code=result.get('error_code'),error_category=result.get('error_category'),
                    rows=len(result.get('data') or [])))
    if args.evidence:
        target=Path(args.evidence)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(evidence,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--ssh')
    mode.add_argument('--local',action='store_true')
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--ssh-command',default='ssh')
    parser.add_argument('--evidence',help='Save bounded verification metadata, no business records')
    parser.add_argument('--native',action='store_true',help='Explicit native read checks, never scale writes or sales sync')
    parser.add_argument('--store',default='mia')
    parser.add_argument('--business-date',default='2026-10-20')
    args=parser.parse_args()
    asyncio.run(check(args))


if __name__=='__main__':
    main()
