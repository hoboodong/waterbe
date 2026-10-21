"""Install only scoped Waterbe Codex discovery instructions and a cwd wrapper.

No model call, existing session interruption, config permission/model change.
"""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import sys

BEGIN='<!-- BEGIN WATERBE MCP STARTUP -->'
END='<!-- END WATERBE MCP STARTUP -->'


def merge(existing,block):
    if BEGIN not in existing and END not in existing:
        return existing.rstrip()+'\n\n'+block.strip()+'\n' if existing.strip() else block.strip()+'\n'
    if existing.count(BEGIN)!=1 or existing.count(END)!=1:
        raise ValueError('ambiguous_existing_scoped_block')
    first,last=existing.index(BEGIN),existing.index(END)+len(END)
    if last<first:
        raise ValueError('invalid_existing_block')
    return existing[:first]+block.strip()+existing[last:]


def install(home,root):
    home,root=Path(home),Path(root)
    block=(root/'config/codex-waterbe-startup.md').read_text(encoding='utf-8')
    target=home/'.codex/AGENTS.md'
    existing=target.read_text(encoding='utf-8') if target.exists() else ''
    updated=merge(existing,block)
    binary=home/'.npm-global/bin/codex'
    if not binary.is_file():
        raise RuntimeError('existing_codex_binary_required')
    evidence=home/'.local/state/waterbe-mcp'/('codex-startup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    evidence.mkdir(parents=True,exist_ok=False,mode=0o700)
    if target.exists():
        shutil.copy2(target,evidence/'previous-global-AGENTS.md')
    launcher=home/'.local/bin/waterbe-codex'
    if launcher.exists():
        shutil.copy2(launcher,evidence/'previous-waterbe-codex')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(updated,encoding='utf-8')
    launcher.parent.mkdir(parents=True,exist_ok=True)
    temporary=launcher.with_suffix('.new')
    temporary.write_text(f'#!/usr/bin/env bash\nset -euo pipefail\nexec "{binary}" -C "{root}" "$@"\n',encoding='utf-8')
    temporary.chmod(0o700)
    os.replace(temporary,launcher)
    bridge=home/'.local/bin/waterbe-mcp-call'
    if bridge.exists():
        shutil.copy2(bridge,evidence/'previous-waterbe-mcp-call')
    client=home/'.local/opt/waterbe-mcp-venv/bin/python'
    bridge.write_text(f'#!/usr/bin/env bash\nset -euo pipefail\nexec "{client}" "{root}/scripts/waterbe_mcp_call.py" "$@"\n',encoding='utf-8')
    bridge.chmod(0o700)
    result=dict(global_instructions=str(target),launcher=str(launcher),mcp_cli=str(bridge),backup=str(evidence),
                model_changed=False,existing_sessions_interrupted=False)
    (evidence/'installation.json').write_text(json.dumps(result)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    if sys.platform!='linux':
        raise SystemExit('ThinkPad Linux installation only')
    print(json.dumps(install(Path.home(),Path(__file__).resolve().parents[1])))
