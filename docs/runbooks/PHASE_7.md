# Phase 7: Engine runtime target

[RUN-001](../tasks/RUN-001-RUNTIME.md) is the authoritative acceptance record.
The Phase 7 hosted entrypoint was `openai_engine_adapter.knowledge_review:app`,
workflow `telecom-journey` version 8. Deployment `deploy-af009ed4` uses build
`bld_01M691YPABN60FEKHW6E1KZGB5`. The repository invoice manifest remains a fixture.

Current rollout: [LANG-2 workflow 9](LANG_2_HOSTED_ROLLOUT.md) uses deployment
`deploy-f11e4d01`; Phase 7 evidence below remains historical.

## Reproduce packaging and local contracts

From the repository root, choose a new, nonexistent temporary destination:

```sh
python3 scripts/prepare_hosted_invoice.py --output /tmp/telecom-runtime-review --profile knowledge-review
uv run --project compatibility/hosted-runtime --frozen --no-sync python -m unittest discover -s tests/hosted_contract -q
```

This credential-free source stage is not a deployment. For a deployable Linux
Python bundle, use the verified archive and compact-runtime options documented in
[Python hosting](../compatibility/PYTHON315_HOSTED.md). Preserve pinned Python 3.15.2,
OpenAI Agents SDK 0.24.0, OpenAI 3.40.0 and Engine SDK/runner 0.11.11.
The stage copies app-owned knowledge modules once from their authoritative sources.
The MIT license is included. Do not upload the repository root or private config.
`scripts/check_hosted_contract.py` is the historical negative native-adapter probe;
its rejection of a raw SDK Agent is not failure of the implemented custom bridge.

## Live acceptance and recovery

Use the [Phase 6 setup](PHASE_6.md) and the existing private CLI backend identity.
Read deployment health by exact deployment ID. For current journey/provider
regressions, use [Phase 5](PHASE_5.md), whose bounded evaluator releases only its
completed runtime reservations. Do not retry uncertain invokes automatically.

For one bounded native recovery proof:

1. Authenticate two existing synthetic users through the application identity service.
2. As the first user, request a simulated change to fiber-1000 in a new conversation.
3. Record the native execution/session and exact pending proposal; verify owner,
   workspace, session and suspended status before any runtime operation.
4. Stop only that session through the native runtime-session stop endpoint and
   confirm its absence with a bounded poll. Preserve durable execution and memory.
5. Recreate the backend service and recover the identical pending action. Verify
   another authenticated user cannot approve and a stale digest cannot resume it.
6. Approve as requester. Require the exact synthetic USD 109.90 receipt, deny a
   duplicate approval, and recover the completed result. Release only that test
   runtime. Preserve sanitized evidence and never export passwords/session tokens.

Runtime stop/recreation does not simulate a platform VM outage. Historical replay
trace counts and current session-level trace limitations are recorded in RUN-001.
Changing workflow versions does not establish migration of pending executions;
resolve owned pending work before a deployment. No Phase 8 stress run is included.
