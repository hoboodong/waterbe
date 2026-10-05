"""Fast-forward published main only; never commit, push, stash, reset or deploy."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


def git(root, *args):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                            text=True, timeout=60, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    if result.returncode:
        raise RuntimeError('git_operation_failed')
    return result.stdout.strip()


def synchronize(root):
    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'status': 'unavailable'}
    try:
        result['before'] = git(root, 'rev-parse', 'HEAD')
        if git(root, 'branch', '--show-current') != 'main':
            result['status'] = 'branch_requires_review'
            return result
        git(root, 'fetch', '--quiet', 'origin', 'main')
        result['published'] = git(root, 'rev-parse', 'origin/main')
        result['tracked_changes'] = bool(git(root, 'status', '--porcelain', '--untracked-files=no'))
        if result['before'] == result['published']:
            result['status'] = 'up_to_date'
        else:
            ahead, behind = map(int, git(root, 'rev-list', '--left-right', '--count', 'HEAD...origin/main').split())
            if ahead:
                result['status'] = 'diverged' if behind else 'needs_push'
            elif result['tracked_changes']:
                result['status'] = 'local_edits_preserved'
            else:
                git(root, 'merge', '--ff-only', 'origin/main')
                result['status'] = 'updated'
        result['after'] = git(root, 'rev-parse', 'HEAD')
    except Exception:
        result['status'] = 'sync_failed'
    return result


def store(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.replace(path)


def observe(database, value, source):
    import history_worker
    history_worker.initialize(database)
    history_worker.health_notice(database, source, value['status'] in ('updated', 'up_to_date'), value['checked_at'])
    history_worker.publish_notices(database, Path.home() / '.local/state/waterbe-central/logs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report-windows', action='store_true')
    args = parser.parse_args()
    if os.name == 'nt':
        state = Path(os.environ['LOCALAPPDATA']) / 'Waterbe/repo-sync.json'
    else:
        state = Path.home() / '.local/state/waterbe-central/repo-sync.json'
    if args.report_windows:
        value = json.load(sys.stdin)
        # Accept only the small status contract, not errors, paths or raw Git output.
        if set(value) - {'checked_at', 'status', 'before', 'after', 'published', 'tracked_changes'}:
            raise ValueError('invalid_sync_report')
        if value.get('status') not in {'updated', 'up_to_date', 'sync_failed', 'branch_requires_review',
                                     'diverged', 'needs_push', 'local_edits_preserved'}:
            raise ValueError('invalid_sync_status')
        datetime.fromisoformat(value['checked_at'])
        store(state.with_name('windows-repo-sync.json'), value)
        observe(Path.home() / '.local/state/waterbe-history/operations.db', value, 'central_windows_sync')
    else:
        value = synchronize(args.root)
        store(state, value)
        if os.name != 'nt':
            observe(Path.home() / '.local/state/waterbe-history/operations.db', value, 'central_repo_sync')
        print(json.dumps(value))
    return 0 if value['status'] in ('updated', 'up_to_date') else 1


if __name__ == '__main__':
    raise SystemExit(main())
