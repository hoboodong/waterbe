"""One migration canary; persist uncertain results and never auto-resend."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys
import uuid

parser = argparse.ArgumentParser()
parser.add_argument('--reporter', type=Path, required=True)
parser.add_argument('--runtime-root', type=Path, required=True)
args = parser.parse_args()
evidence = args.runtime_root / 'thinkpad-migration-test.json'
if evidence.exists():
    raise SystemExit('Canary already attempted; inspect existing evidence')
spec = importlib.util.spec_from_file_location('migration_reporter', args.reporter)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
config = module.load_config(args.runtime_root / 'config.json')
code, output = module.execute_test(config=config, client=module.TelegramClient(module.validate_token(os.environ)),
                                  test_id=str(uuid.uuid4()), now=module.utc_now())
module.atomic_write_json(evidence, output)
print('migration_canary_' + output['status'])
raise SystemExit(code)
