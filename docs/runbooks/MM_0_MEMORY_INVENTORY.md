# MM-0: memory migration inventory

> Historical preservation-first checkpoint. The requester later accepted dev memory
> loss and authorized the project-store dependency copy. The applied result and
> current limits are in [MM_DEV_CUTOVER](MM_DEV_CUTOVER.md); blockers below are
> preserved as history, not current dev-cutover status.

## Current gate — 2026-11-02

MM-0 is incomplete. No source/target memory write, configuration apply, deployment,
session cancellation or data transfer has been performed. [MEM-002](../tasks/MEM-002-MYMEMORY-MIGRATION.md)
owns the phase gates. The user's instruction to proceed retains the default
preservation requirement; it does not imply starting with empty memory.

## Read-only observations

- Agent Engine CLI: `0.1.120`. The local private Engine project matches the selected
  named context. The adapter directory has no usable CLI project pin; explicit
  context selection corrected the initial `no project target found` error.
- `workspace list --context <verified-context> --json`: two workspaces, `agentsdk`
  and `geo-intelligence-network`, both with memory enabled. A project-level change
  affects both; no workspace-only memory switch has been established.
- `memory status --context <verified-context>` repeatedly returned
  `state: provisioning`, `blocked_on: orchestration_engine`. This does not prove
  data loss or identify the underlying infrastructure cause. Native recall and
  applied runtime version cannot currently be certified.
- Session listing initially rejected combining `--context` with `--workspace-id`.
  Retrying with explicit base URL, organization/project/workspace IDs reached the
  service, but both workspace requests returned HTTP 504 Gateway Timeout. Active
  writers/drain state therefore remain unknown; no session was stopped.
- Private destination inputs are populated. URI scheme is `mongodb+srv`; its host
  matches the private target host; credential fields and project ID are present.
  This is syntax/coherence validation, not DNS/TLS/auth or destination identity proof.
- Atlas inventory failed in the sandbox and again with network access. Sanitized
  stderr identified `session expired`; this is authentication failure, not evidence
  that mymemory is missing or incompatible. Atlas login was initiated. Initial
  noninteractive login failed at the account-type prompt with EOF; an interactive
  retry reached device authorization. Destination inventory remains pending login.

No private URI, credential, device code, memory contents or profile data is recorded.

## Migration support review

Official documentation search confirmed project-scoped configuration and the
distinction between storing configuration and applying it at runtime:

- [Memory configure](https://www.mongodb.com/docs/agentengine/cli/agentengine_memory_configure/)
- [Memory apply](https://www.mongodb.com/docs/agentengine/cli/agentengine_memory_apply/)
- [Memory SDK](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk-memory/)

The results did not establish an Engine-supported existing-memory transfer recipe.
Generic Atlas restore documentation is not sufficient proof of Engine state,
partition/index compatibility or rollback after target writes. CLI `migrate`
concerns agent configuration/SDK surfaces, not a verified managed-memory transfer.
No configure/apply/upgrade or restore command was run.

## Next gates

1. Connectivity, cluster identity and shared-consumer scope are resolved below.
   Finish complete target visibility, TTL/unique definitions and access-scope proof.
2. Establish a bounded native two-user recall baseline and background writer drain
   procedure; runtime readiness and zero reserved sessions alone are insufficient.
3. Verify a supported complete transfer and index-readiness procedure, including
   consistency point and post-write rollback. Both workspaces may move together.
4. Present the exact target preparation/switch actions, affected consumers and
   rollback implications before any shared mutation, as required by AGENTS.md and
   MEM-002. Source deletion and empty-memory fallback remain excluded.

## Connectivity recovery after operator resume

The operator completed Atlas login and resumed the relevant clusters. Atlas inventory
then showed source `ClusterDemoTelco` (MongoDB 9.0.4, M30_GEN_2), target `mymemory`
(9.0.4, M20) and `OpenAI-SDK` (9.0.4, M20) with `paused=false`. Source was REPAIRING,
application UPDATING and target IDLE at that observation. The target SRV matched
its private input. Source/target reported backupEnabled=false and pitEnabled=false;
application reported both true. This inventory does not establish a usable restore.

Executed `mongosh --nodb --quiet --file /tmp/telecom_mm0_connections.js`: all three
configured connections passed `ping` and `connectionStatus` with an authenticated
principal and normal TLS certificate/hostname validation. Clients were sequential,
reused for the two commands and closed. Diagnostic timeouts bound this local probe;
no application pool settings changed. [Sanitized evidence](../../compatibility/mm0-connection-evidence.json)
records timings and outcomes without URIs or credentials. No data was written.

The initial Python helper could not start: the local 3.15.2 interpreter's standard
library lacked encodings sources. The same initialization error occurred outside
the sandbox, before any database request. No downgrade or application environment
change was made. The alternative mongosh helper initially failed to parse explicit
await in its script context; removing it to use shell evaluation semantics corrected
the harness, and all three real probes then passed. These failures were local probe
setup failures, not database connectivity failures. Python application validation
must resolve its interpreter separately before being claimed anew.

After connectivity passed, `agentengine memory status --context <verified-context>`
reported `state: ready`. This supersedes the earlier readiness/authentication blockers,
not the unverified session/drain inventory or existing-memory transfer compatibility.
Two-user recall, target contents/index compatibility and supported migration remain
unrun. No memory destination change or live migration was performed.

Local `python3 scripts/check_repository.py` and `git diff --check` passed after this
checkpoint; no application regression suite, PR/CI or deployment is claimed.

## Verified source mapping and index inventory

A later Atlas host comparison corrected an initial helper label: local MONGODB_URI
also targets OpenAI-SDK. It is not the project's managed-memory secret and must not
be substituted for it. The source-labelled local metadata probe saw seven authorized
application databases and no expected memory database because it was on OpenAI-SDK;
this is not missing source memory. The connection JSON now records this correction.

The existing ClusterDemoTelco MCP connector successfully read the expected project's
memory database: 12 collections, 1,421 documents by database metadata, 13,564,850 logical
data bytes and 80 classic indexes. Collection-index inventory additionally found
12 search/vector indexes, all READY and queryable. The tool does not expose complete
TTL/unique options, so those are still unverified. These are metadata observations,
not retrieval acceptance or a consistent backup point. Managed task/scheduling/config
collections are present alongside the memory collections; copying only semantic and
episodic documents would omit managed state.

The target credential sees zero authorized non-system databases and no expected
project memory database. Authorized visibility alone does not prove a globally empty
cluster. [Inventory evidence](../../compatibility/mm0-inventory-evidence.json) records
only counts, collection/index names and status, never content or connection strings.

After recovery, explicit session-list commands succeeded for both workspaces, each
returning count 0. This resolves the earlier HTTP 504 observation; it does not prove
background extraction is drained or prevent new sessions from starting. Shared
consumer scope was resolved on 2026-11-02: the requester confirmed "sim eles podem
migrar juntos" for agentsdk and geo-intelligence-network. No cutover is authorized
by these observations alone. Supported complete transfer, TTL/partition preservation,
background-write quiescence and a new native two-user recall baseline remain gates.

## Joint migration decision and remaining compatibility gate

The requester confirmed both workspaces may migrate together on 2026-11-02. The
scope decision is resolved and must not be requested again. Preserve the existing
project, workspace/user/session identifiers and all managed state; no empty-memory
fallback is authorized.

Read-only CLI inspection confirms Engine CLI 0.1.120 exposes memory configure,
apply and status. Apply rolls the memory runtime; it is not a backup or a verified
extraction-drain command. Installed mongodump/mongorestore are **100.11.0** on macOS
ARM64. Official current [mongodump compatibility](https://www.mongodb.com/docs/database-tools/mongodump/mongodump-compatibility-and-installation/)
and [mongorestore compatibility](https://www.mongodb.com/docs/database-tools/mongorestore/mongorestore-compatibility-and-installation/)
explicitly list MongoDB 9.0 for **100.20.0**. The current documentation does not
certify the installed older binaries for this source. No tool upgrade, dump or
restore has been performed.

Candidate procedure to validate, not an executable/approved migration:

1. Use an Engine-supported mechanism to stop new writes from both workspaces and
   drain extraction, scheduled work and in-progress tasks. Verify the final
   consistency point; zero reserved sessions is not this proof.
2. With a verified compatible tool version and appropriately scoped administrative
   access, preserve the entire project-managed state, collection metadata and IDs.
   Confirm whether anything outside the observed memory database must accompany it.
3. Restore only into an approved isolated rehearsal destination; preserve TTL,
   unique/index options, timestamps, partition keys and embedding dimensions.
   Explicitly recreate/verify search indexes using the supported procedure.
4. Run two-user recall/isolation and application regression before changing the
   live project secret. Final cutover requires an exact separate mutation proposal,
   existing config recovery information and proof of active target attachment.
5. Before target writes, restore the verified old config if needed. After target
   writes, keep both stores and freeze writes until supported reverse transfer or
   reconciliation succeeds; do not promise immediate lossless switch-back.

The blocking evidence needed from an authoritative Engine procedure is concrete:
(a) supported writer/extraction quiescence and resume commands for this runtime;
(b) complete managed-state backup/restore boundaries and required companion state;
(c) supported connection-secret application/attachment verification and rollback
with target writes. Official configuration documentation and generic Database Tools
compatibility do not establish those Engine-specific guarantees. No support request
has been sent to anyone. MM-0 remains incomplete; MM-1–5 must not begin on an invented
procedure. This is a technical compatibility dependency, not another request to
approve migrating the two workspaces together.

## Transfer review handoff

[Prepared technical review](MM_0_TRANSFER_REVIEW.md) consolidates the unresolved
writer-drain, managed-state, metadata and rollback questions. No external support
message was sent. The current checkpoint is a blocked compatibility gate, not a
completed MM-0 phase; any draft PR preserves that status.
