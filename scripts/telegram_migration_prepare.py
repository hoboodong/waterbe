"""Remap only the reporter's triage root; preserve event IDs and delivery state."""
import argparse
import importlib.util
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--state-root', type=Path, required=True)
parser.add_argument('--reporter', type=Path, required=True)
parser.add_argument('--import-logs', type=Path)
args = parser.parse_args()
if args.import_logs:
    for path in args.import_logs.glob('worker-*.jsonl'):
        target = args.state_root / 'logs' / (path.stem + '.000-windows.jsonl')
        if target.exists():
            if target.read_bytes() != path.read_bytes():
                raise RuntimeError('import_log_collision')
        else:
            with target.open('xb') as output:
                output.write(path.read_bytes())
config_path = args.state_root / 'telegram-failure-reporter/config.json'
config = json.loads(config_path.read_text(encoding='utf-8-sig'))
config['triage_runtime_root'] = str(args.state_root / 'local-codex-triage')
spec = importlib.util.spec_from_file_location('migration_reporter', args.reporter)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.atomic_write_json(config_path, config)
module.load_config(config_path)
outbox = module.load_outbox(config_path.parent / 'outbox.json', module.utc_now())
print(json.dumps({'items': len(outbox['items']), 'uncertain': sum(x['status'] == 'delivery_uncertain' for x in outbox['items'].values()), 'configuration_valid': True}))
