"""Apply only the three explicitly approved Phase 4 Engine tool names."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, build_opener

from compatibility.demo_auth.engine import BASE, PROJECT, NoRedirect

POLICY = '6ae1ab6186dc82d1c54886b1'
NAMES = ['telco_request_ingestion', 'telco_search_knowledge', 'telco_publish_knowledge']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-approved', required=True, action='store_true')
    parser.parse_args()
    credential = json.loads((Path.home() / '.agentengine/auth.json').read_text())
    token = credential['credentials'][BASE]['access_token']

    def call(path='', data=None):
        request = Request(BASE + f'/api/v1/projects/{PROJECT}/policies' + path,
                          method='GET' if data is None else 'PUT',
                          data=None if data is None else json.dumps(data).encode(),
                          headers={'Authorization': 'Bearer ' + token,
                                   'Content-Type': 'application/json'})
        with build_opener(NoRedirect()).open(request, timeout=30) as response:
            return json.load(response)

    before = call()['policies']
    policy = next(item for item in before if item['id'] == POLICY)
    assert policy['type'] == 'AUTHORIZED_TOOLS' and policy['enabled'] is True
    current = policy['string_list']
    additions = [name for name in NAMES if name not in current]
    target = current + additions
    # Save the fresh snapshot before the mutation, never use the older proposal as a PUT body.
    snapshot = Path('artifacts/compatibility/phase4-policy-before.json')
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(json.dumps(before, indent=2) + '\n')
    if additions:
        call('/' + POLICY, {'string_list': target})
    after = call()['policies']
    updated = next(item for item in after if item['id'] == POLICY)
    assert updated['string_list'] == target and updated['enabled'] is True
    assert {p['id'] for p in before} == {p['id'] for p in after}
    for item in before:
        other = next(p for p in after if p['id'] == item['id'])
        if item['id'] != POLICY:
            assert item == other
        else:
            # Server-managed update timestamps may change on the updated policy only.
            for key, value in item.items():
                if key not in ('string_list', 'updated_at', 'updatedAt'):
                    assert other.get(key) == value, key
    evidence = {'checked_at': datetime.now(UTC).isoformat(), 'policy_id': POLICY,
                'status': 'applied_control_plane_verified', 'added': additions,
                'before_count': len(current), 'after_count': len(target),
                'other_policies_unchanged': True,
                'limitations': ['Tool runtime propagation and hosted integration pending',
                                'No publication or deployment enabled by this operation']}
    Path('compatibility/phase4-engine-policy-evidence.json').write_text(
        json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Policy operation stopped: {type(error).__name__}, code={getattr(error, "code", None)}')
        raise SystemExit(1) from None
