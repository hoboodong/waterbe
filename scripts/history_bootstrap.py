"""Scheduled central entry point. Load only explicitly configured user env keys."""
import os
import winreg
import history_worker

with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as environment:
    for name in ('SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY'):
        if not os.environ.get(name):
            try:
                value,_=winreg.QueryValueEx(environment,name)
                os.environ[name]=value
            except OSError:
                pass

if __name__ == '__main__':
    raise SystemExit(history_worker.main())
