"""Call the same MCP from existing Codex sessions without replacing their conversation.

This is a transport client, not a separate operation implementation or AI agent.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
from mcp import Client,StdioServerParameters

TOOLS={'waterbe_start','waterbe_find_guides','waterbe_read_guide','waterbe_list_operations',
       'waterbe_describe_operation','waterbe_call','waterbe_prepare_action',
       'waterbe_submit_action','waterbe_action_status','waterbe_check_connections'}


async def call(tool,arguments):
    if tool not in TOOLS or not isinstance(arguments,dict):
        return {'status':'invalid_request','reason':'Registered MCP tool and object arguments required'}
    async with Client(StdioServerParameters(command=str(Path.home()/'.local/bin/waterbe-mcp')),
                      mode='legacy',read_timeout_seconds=180) as client:
        result=await client.call_tool(tool,arguments)
        if result.is_error:
            return {'status':'unavailable','reason':'MCP tool returned an error; inspect original operation ID'}
        return result.structured_content or {'status':'unavailable','reason':'No structured response'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tool',choices=sorted(TOOLS))
    parser.add_argument('--arguments',default='{}',help='JSON object, or - to read stdin; never pass secrets')
    args=parser.parse_args()
    try:
        raw=sys.stdin.read() if args.arguments=='-' else args.arguments
        if len(raw.encode())>65536:
            raise ValueError('input_too_large')
        result=asyncio.run(call(args.tool,json.loads(raw)))
    except (ValueError,TypeError):
        result={'status':'invalid_request','reason':'Bounded JSON object required'}
    except Exception:
        result={'status':'unavailable','reason':'MCP connection failed; do not replay uncertain writes'}
    print(json.dumps(result,ensure_ascii=False))
    return 1 if result.get('status') in ('unavailable','invalid_request','unsupported') else 0


if __name__=='__main__':
    raise SystemExit(main())
