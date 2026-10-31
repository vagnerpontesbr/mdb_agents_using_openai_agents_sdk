"""Read the current Engine policy and write the exact Phase 4 proposal; never apply it."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from telecom_app.journey import EngineAPI


def main():
    policies = EngineAPI().call('policies')['policies']
    policy = next(item for item in policies if item['id'] == '6ae1ab6186dc82d1c54886b1')
    if policy['type'] != 'AUTHORIZED_TOOLS' or policy['enabled'] is not True:
        raise ValueError('Unexpected policy configuration')
    tools = {
        'telco_request_ingestion': {
            'purpose': 'Enqueue a bounded uploaded PDF for an authenticated curator',
            'required_controls': ['Server-derived tenant and curator permission',
                                  'Authorized original PDF and exact metadata digest',
                                  'Idempotent four-slot admission; OCR stays in the worker'],
        },
        'telco_search_knowledge': {
            'purpose': 'Return current authorized technical procedures with exact citations',
            'required_controls': ['Server-derived tenant, ACL and equipment applicability',
                                  'Native hybrid search and authoritative eligibility rechecks',
                                  'Bounded contextual embedding/reranking and extractive output'],
        },
        'telco_publish_knowledge': {
            'purpose': 'Publish an exact staged document version after native Engine review',
            'required_controls': ['Verified native decision, requester and action digest',
                                  'Current owner, source, dates and publication permissions',
                                  'Atomic version activation/replacement and idempotent receipt',
                                  'Fail closed on missing, rejected, expired or mismatched review'],
        },
    }
    before = policy['string_list']
    if not isinstance(before, list) or any(not isinstance(name, str) for name in before):
        raise ValueError('Unexpected tool allowlist')
    additions = [name for name in tools if name not in before]
    proposal = {
        'status': 'proposed_not_applied_requires_explicit_user_approval',
        'observed_at': datetime.now(UTC).isoformat(),
        'project_id': '67b385a7976edf15ecc62e06',
        'policy_id': policy['id'], 'policy_type': policy['type'],
        'scope': 'Shared project policy; affects every workspace in the project',
        'intended_deployment_workspace': 'ws-6ae20f53f3b040aa65fa961a',
        'method': 'PUT',
        'path': '/api/v1/projects/67b385a7976edf15ecc62e06/policies/' + policy['id'],
        'observed_before': before, 'additions': additions,
        'proposed_body': {'string_list': before + additions}, 'tools': tools,
        'observed_all_policies_sha256': hashlib.sha256(
            json.dumps(policies, sort_keys=True).encode()).hexdigest(),
        'application_rules': [
            'Re-read immediately before application and union only the approved names',
            'Preserve every existing tool and every unrelated policy field',
            'Verify other policies unchanged and exact policy propagation',
            'Tool authorization alone does not enable publication or prove compatibility',
            'Keep document tools unavailable until backend/native review controls pass',
            'No change to model, memory, platform budgets or other workspace deployments',
        ],
    }
    Path('compatibility/phase4-engine-policy-proposal.json').write_text(
        json.dumps(proposal, indent=2) + '\n')
    print(json.dumps({'status': proposal['status'], 'current_count': len(before),
                      'proposed_count': len(before) + len(additions), 'additions': additions}))


if __name__ == '__main__':
    main()
