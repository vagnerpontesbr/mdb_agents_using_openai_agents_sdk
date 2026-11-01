# Telecom Agent Reference Asset

A telecom customer-service reference using OpenAI Agents SDK for orchestration,
MongoDB Agent Engine for managed platform capabilities, MongoDB Atlas, Voyage AI,
and Python managed by uv. The bounded implementation includes a supervisor,
financial/technical/sales specialists, React chat/voice, and governed PDF retrieval.

**Phases 0–7 are published with passing CI. Phase 8 scalability/resilience is complete for the approved demo scope; manual publication is pending: [OPS-001](docs/tasks/OPS-001-RESILIENCE.md) records short local HTTP
characterization, sustained/Atlas/voice acceptance and the final requester scope decision.** Start with
[the handoff runbook](docs/runbooks/PHASE_6.md), then read the
[current runtime contract](docs/runbooks/PHASE_7.md) and
[acceptance evidence](docs/tasks/RUN-001-RUNTIME.md).
[Decisions](docs/adr/README.md) and [publication status](docs/runbooks/REPOSITORY_SETUP.md)
distinguish accepted scope, historical checkpoints and current Git/CI results.

## Run the application foundation

The new React account workspace supports login, administrator-only registration,
session restoration and logout through the existing MongoDB identity boundary.
The authenticated workspace now uses Support/Knowledge navigation and a Profile
menu. Administrators create accounts under Control Plane → Users. Name, timezone and interface language editing are implemented with validated Atlas persistence. Profile photo add/replace/remove is implemented with private normalized thumbnails.
Self-service password change is implemented with current-password verification and
session invalidation. Upgrade all identity-serving processes before enabling it; see
the [application runbook](docs/runbooks/APPLICATION.md). Settings and Tokenomics data remain pending in the [UI plan](docs/tasks/UI-001-PROFILES-CONTROL-PLANE.md).
Chat, specialists and voice are opt-in under the [Phase 2 runbook](docs/runbooks/PHASE_2.md)
and are disabled by default until configured against the accepted deployment. The [application runbook](docs/runbooks/APPLICATION.md)
provides prerequisites, private configuration, optional index/bootstrap commands,
and the API contract.

```sh
uv sync --frozen --python /path/to/python3.15
npm --prefix apps/web ci
npm --prefix apps/web run build
uv run --frozen --env-file .env telecom-api --port 8000
```

Open `http://127.0.0.1:8000` with the configured existing demo account. Python must
be 3.15.2; configure `APP_WEB_DIST=apps/web/dist` and the restricted application
cluster URI as documented. Existing users are not reset.

## What works in the bounded demo

- A custom hosted adapter runs the real OpenAI Runner through Engine model/tool
  proxies, with native review/resume and bounded replay/recovery controls.
- Engine semantic/episodic memory recall, user isolation and chat/voice continuity
  passed. Engine remains the only managed-memory owner.
- The loopback identity UI supports email/password, `user`/`admin` roles,
  admin-only registration and original-requester approval. A restricted MongoDB
  identity accesses only the demo authentication collections on OpenAI-SDK.
- Real browser microphone capture, Engine execution, speech output and explicit
  human listening passed. Voice acceptance is limited to a quiet environment.
- Search/Auto Embedding/native fusion, scoped filters, Voyage HTTP, and synthetic
  textual/scanned PDF parsing have bounded compatibility evidence.
- Local fault controls and an injected hosted dependency failure were exercised.
  The normal recall build was restored and its positive control passed.

The [Phase 0 checkpoint](docs/compatibility/PHASE_0.md) is authoritative for versions,
test counts, scope and evidence. The [demo runbook](docs/runbooks/DEMO.md) provides
startup commands and the [adapter guide](compatibility/openai_engine_adapter/README.md)
explains runtime ownership and unsupported contracts.

## Accepted limits and next work

Exact chronological history restoration is outside demo scope. The backend uses
the operator's private Engine CLI login as an explicit local-demo exception.
Native memory expiry is accepted without additional deletion proof. No production
outage/capacity guarantee, remote cancellation guarantee or noisy-speech accuracy
claim follows from the tests. See ADRs [0021](docs/adr/0021-demo-semantic-episodic-continuity.md),
[0022](docs/adr/0022-demo-private-engine-cli-identity.md) and
[0023](docs/adr/0023-quiet-environment-demo-voice.md).

The user authorized Phase 2; [journey evidence](docs/tasks/VERT-001-JOURNEY.md)
records local tests, live acceptance and the final audio correction. Governed ingestion, RAG quality
evaluations and load profiles remain later phases in the [backlog](docs/tasks/README.md).

## Documentation and contribution

- [Implementation plan](initial_plan.md) and [requirements](docs/REQUIREMENTS.md)
- [Architecture decisions](docs/adr/README.md) and [data boundaries](docs/DATA_ARCHITECTURE.md)
- [Document governance](docs/DOCUMENT_GOVERNANCE.md) and [stale-document example](examples/telecom/governance/README.md)
- [Best practices](docs/BEST_PRACTICES.md), [voice design](docs/research/voice-agents.md), and [scalability plan](docs/SCALABILITY_AND_STRESS_TESTS.md)
- [Contributor commands](CONTRIBUTING.md), [agent instructions](AGENTS.md), and [security](SECURITY.md)

All documentation, code and user-facing demo content is in English. Run
`python3 scripts/check_repository.py` for repository structure and local link
validation; it is not an application or provider test.

## License

Original project code is distributed under the [MIT License](LICENSE). Third-party
dependencies and hosted services retain their own licenses and terms. This is an
independent reference asset, not an official MongoDB product.
