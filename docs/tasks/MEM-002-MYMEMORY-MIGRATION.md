# MEM-002: Move Engine-managed memory to mymemory

- Status: Planned; destination and migration compatibility not verified
- Requested: 2026-11-01
- Owner: Telecom demo maintainer
- Dependencies: MEM-001, COMP-002, existing Engine project/workspace inventory
- Decision: [ADR-0031](../adr/0031-mymemory-target.md)
- Related interface work: [UI-001](UI-001-PROFILES-CONTROL-PLANE.md), [TOK-001](TOK-001-TOKENOMICS.md)

## Requested outcome and current boundary

Plan moving Agent Engine memory from `ClusterDemoTelco` to the dedicated
`mymemory` cluster. Application identity, knowledge, ingestion and eval/load data
stay on `OpenAI-SDK`. Engine remains the only managed-memory owner; the SDK and
FastAPI must not gain a direct memory writer. The requester intends to change the
DemoTelco project later; that project migration is not included in this execution.

Current application/memory segregation already exists under ADR-0017. This change
replaces the memory destination; it does not move application data. The cluster
name `mymemory` is requester-supplied. Its actual SRV host, Atlas project, version,
tier, network access and existing contents have not been verified.

Memory configuration is project-scoped, not isolated by workspace. Inventory all
consumers before changing the current project's secret/configuration. If DemoTelco
or another workspace shares that project, a project-wide switch can affect it now.
MM-0 must resolve whether all affected consumers can move in one window. Otherwise
prepare a separate Engine-project/isolation design and identity/deployment mapping;
do not silently create a project or claim that a workspace-only secret isolates it.

## Private configuration

Add these empty placeholders to `.env.example` and the ignored local `.env`:

```dotenv
MYMEMORY_MONGODB_URI=
MYMEMORY_CLUSTER_HOST=
MYMEMORY_ATLAS_PROJECT_ID=
```

The URI is supplied privately by the operator; do not invent an SRV address or use
credentials from another cluster. `MYMEMORY_CLUSTER_HOST` is the verified SRV host,
without credentials or path. Empty values disable any future migration preflight.
No secret value belongs in Markdown, reports, command arguments, screenshots or Git.
Keep `.env` private and ignored; preserve all existing values.

These are local administrative input names only. They are not an Engine API or a
runtime integration. The current project uses the Engine secret `MONGODB_URI` for
managed memory; MM-0 must verify the pinned deployment's exact supported secret
scope and application/restart procedure before mapping the new input to it.
Do not replace the existing local `MONGODB_URI`, `APP_MONGODB_URI`, knowledge URIs,
or egress configuration while planning. Changing `.env` alone does not move memory.

## Data preservation and rollback policy

Default proposal: preserve existing semantic/episodic memory and stable identity
and session mappings. Starting empty is a separate explicit decision, not an
automatic fallback when migration is unsupported. Exact chronological history
remains outside the demo contract, but inventory any supporting managed state
required for continuity before transferring data.

Use only a verified supported Engine/Atlas backup-transfer-restore method. Current
documentation search establishes configuration/application and egress mechanics,
not a supported existing-memory migration recipe. MM-0 must prove compatibility
or record the gate as blocked. Do not use application code to recreate managed
collections or copy selected documents while omitting supporting state.

Preserve data types, IDs, source timestamps, TTL definitions, partition metadata,
models/dimensions and managed collection names. Search indexes may need separate
recreation/readiness checks; a successful data restore is not search readiness.
Do not reset expiry dates or re-embed by default. Native 30-day expiry remains
accepted; no new physical-expurgo demonstration is required.

Quiesce affected writers and drain/resolve active runs and extraction work before
the final consistency point. Keep one active destination; no competing dual writer.
Before the first write on mymemory, rollback may restore the old verified config.
After target writes, switching back can lose new memories: freeze writes, retain
both stores, and use a verified reverse-transfer/reconciliation procedure before
restoring service. If unavailable, keep the change window closed for diagnosis;
never advertise unconditional zero-loss rollback. Source deletion is excluded.

## Phases and tests after each change

| Phase | Change / deliverable | Required verification before advancing |
| --- | --- | --- |
| MM-0 — Inventory and compatibility | Read-only source/target and Engine inventory; affected workspaces; exact supported migration/runbook; private destination input validation | Confirm cluster identity and scope, shared-consumer impact, supported backup/restore, baseline two-user recall and app operation; record versions and redacted manifest. Missing URI or unsupported migration blocks execution, not planning |
| MM-1 — Destination preparation | Exact scoped role/network/index proposal, then approved provisioning on mymemory | Engine identity allowed only required managed resources; application identities denied memory access; DNS/TLS/auth checks; required index/config compatibility; target changes isolated from application and source. Do not broaden roles or create a cluster silently |
| MM-2 — Rehearsal | Supported restore/transfer into an isolated destination context; source unchanged | Compare scoped inventory/counts/hashes without content logs; stable IDs/timestamps/TTL; native index readiness; two-user memory recall and denial; rehearsal rollback. Temporary context resources must be included in the proposal |
| MM-3 — Controlled switch | Freeze affected writers, final consistent transfer, update exact Engine secret/config, apply/restart using verified pinned commands | Verify runtime applied generation and actual target attachment, not just secret presence or `ping`; canary write/read via Engine on mymemory; old source shows no new canary writes; preserve application-cluster connectivity and egress |
| MM-4 — Regression and acceptance | Resume bounded synthetic traffic after canary; exercise app workflow | Same-session and new-session semantic/episodic continuity; two-user isolation; chat/voice share the same memory behavior; requester approvals/recovery; controlled unavailable-target failure with no false success/fallback; application login and governed knowledge still pass |
| MM-5 — Handoff | Update topology and Control Plane observation metadata; preserve source backup and DemoTelco follow-up boundary | Recheck redaction, target identity, rollback instructions and evidence. Record later DemoTelco project work explicitly; no source cleanup, extra capacity test or pricing proof required |

Every change receives its own positive and negative checks before another change.
Record an evidence row per phase: commit/config version, source/destination IDs,
affected consumers, exact actions, tests/results, index readiness, rollback state
and unresolved gaps. Freeze on failed isolation, missing memory, uncertain writes
or application regression. Never retry an uncertain migration step blindly.

Connection clients for future probes must be reused, explicitly closed and bounded.
Use driver defaults unless measured probe concurrency justifies a change. Preserve
Engine-owned runtime pools; record connection churn/waits during the bounded checks
without inventing new pool limits or presenting local connectivity as Engine access.

## Integration sequence

UI design/shell work can proceed independently. Run each MM phase in a separate
change window from UI rollout so failures can be attributed. UI-3 may show current
and planned memory targets with explicit observation timestamps; it must not offer
a URI editor or a migration button. UI final acceptance verifies the actually active
target after MM-4, or clearly labels migration pending if the tracks ship separately.
Tokenomics must preserve workspace/project attribution and migration boundaries;
it cannot combine old/new observations as duplicate usage.

## Sources and evidence

- [Engine memory configuration](https://www.mongodb.com/docs/agentengine/add-features/memory/): project-scoped configuration.
- [Memory SDK/configuration](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk-memory/): storing configuration differs from applying it; model/dimension changes affect data/index compatibility.
- [Atlas egress linking](https://www.mongodb.com/docs/agentengine/network-egress/atlas-cluster-link/): changing a linked cluster changes egress; other destinations need appropriate access.

Planning consulted these official documentation excerpts. No migration command,
configuration apply, runtime upgrade, cluster connection, data copy, provider test
or live write was executed. All MM phase gates are unrun. Existing source topology
and historical evidence remain current until successful cutover acceptance.
