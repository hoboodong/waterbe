"""Read-only cross-project CASPi contract check; never connects to a scale."""
import argparse
import hashlib
import json
from pathlib import Path


def check(cas_repo, app_repo):
    canonical = Path(cas_repo) / 'contracts/caspi-v1.json'
    mirror = Path(app_repo) / 'test/fixtures/caspi-v1.json'
    expected = json.loads(canonical.read_text(encoding='utf-8'))
    actual = json.loads(mirror.read_text(encoding='utf-8'))
    if expected != actual:
        raise ValueError('caspi_contract_fixture_mismatch')
    digest = hashlib.sha256(json.dumps(expected, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()
    return {'status': 'matched', 'protocol_version': expected['protocol_version'],
            'contract_revision': expected['contract_revision'], 'sha256': digest,
            'live_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cas-repo', required=True, type=Path)
    parser.add_argument('--app-repo', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.cas_repo, args.app_repo)))
