"""Install the requested STDIO MCP release on the central Linux host only.

Run from a verified source package after installing the dedicated requirements.
No worker restart, business operation, model invocation or credential copying.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

FILES = ('waterbe_mcp.py','waterbe_api.py','system_check.py')


def main():
    if sys.platform != 'linux':
        raise RuntimeError('central_linux_required')
    root = Path(__file__).resolve().parents[1]
    home = Path.home()
    interpreter = home/'.local/opt/waterbe-mcp-venv/bin/python'
    subprocess.run([str(interpreter),'-c','from mcp.server import MCPServer'], check=True)
    hashes = {name:hashlib.sha256((root/'scripts'/name).read_bytes()).hexdigest() for name in FILES}
    digest = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
    release = home/'.local/lib'/('waterbe-mcp-'+digest)
    release.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in FILES:
        target = release/name
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != hashes[name]:
                raise RuntimeError('immutable_release_conflict')
        else:
            shutil.copy2(root/'scripts'/name,target)
    launcher = home/'.local/bin/waterbe-mcp'
    evidence = home/'.local/state/waterbe-mcp'/('install-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    evidence.mkdir(parents=True, mode=0o700)
    if launcher.exists():
        shutil.copy2(launcher,evidence/'previous-launcher')
    if not (home/'.config/waterbe/central.env').is_file():
        raise RuntimeError('existing_central_environment_required')
    # Existing central credentials stay on this host. The existing read-only
    # code and environment are reused; no copy of the secret file is made.
    text = f'''#!/usr/bin/env bash
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/.local/gog-bin:/usr/bin:/bin:${{PATH:-}}"
set -a
source <(tr -d '\\r' < "$HOME/.config/waterbe/central.env")
set +a
export WATERBE_ROOT="{root}"
export WATERBE_CENTRAL_LOCAL=1
export PYTHONPATH="{root}/scripts:${{PYTHONPATH:-}}"
exec "{interpreter}" "{release}/waterbe_mcp.py"
'''
    launcher.parent.mkdir(parents=True,exist_ok=True)
    temporary = launcher.with_suffix('.new')
    temporary.write_text(text,encoding='utf-8')
    temporary.chmod(0o700)
    os.replace(temporary,launcher)
    result = dict(installed_at=datetime.now(timezone.utc).isoformat(),
                  release=str(release), source_root=str(root), hashes=hashes,
                  launcher=str(launcher), evidence=str(evidence),
                  protocol_verified=False, business_mutations=0)
    (evidence/'installation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
