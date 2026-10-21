"""Set only Waterbe MCP timeouts after native `codex mcp add`; preserve other settings."""
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import tomllib


def main():
    path=Path.home()/'.codex/config.toml'
    text=path.read_text(encoding='utf-8')
    parsed=tomllib.loads(text)
    assert 'waterbe' in parsed.get('mcp_servers',{}), 'register_waterbe_first'
    match=re.search(r'(?m)^\[mcp_servers\.waterbe\]\s*$',text)
    assert match, 'explicit_waterbe_table_required'
    end=re.search(r'(?m)^\[',text[match.end():])
    stop=match.end()+end.start() if end else len(text)
    section=text[match.end():stop]
    section=re.sub(r'(?m)^(startup_timeout_sec|tool_timeout_sec)\s*=.*\n?', '',section)
    updated=text[:match.end()]+'\nstartup_timeout_sec = 30\ntool_timeout_sec = 180\n'+section+text[stop:]
    result=tomllib.loads(updated)
    for key,value in parsed.items():
        if key!='mcp_servers':
            assert result[key]==value
    for name,value in parsed['mcp_servers'].items():
        if name!='waterbe':
            assert result['mcp_servers'][name]==value
    backup=path.with_name('config.toml.before-waterbe-timeouts-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    shutil.copy2(path,backup)
    path.write_text(updated,encoding='utf-8')
    print('waterbe startup_timeout_sec=30 tool_timeout_sec=180; other settings preserved')


if __name__=='__main__':
    main()
