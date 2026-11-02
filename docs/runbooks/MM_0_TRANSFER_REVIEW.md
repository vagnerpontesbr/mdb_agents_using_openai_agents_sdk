# MM-0: managed-memory transfer review

> Historical preservation-first checkpoint. The requester later accepted dev memory
> loss and authorized the project-store dependency copy. The applied result and
> current limits are in [MM_DEV_CUTOVER](MM_DEV_CUTOVER.md); blockers below are
> preserved as history, not current dev-cutover status.

## Status and scope

Prepared for technical review; not a supported execution recipe. No request has
been sent to MongoDB or another party. [MEM-002](../tasks/MEM-002-MYMEMORY-MIGRATION.md)
requires preservation and a supported complete transfer before live mutation.
[Inventory](MM_0_MEMORY_INVENTORY.md) records observed environment and failures.

The requester approved moving `agentsdk` and `geo-intelligence-network` together.
Both belong to the same Engine project. Keep project/workspace/user/session identity,
Engine ownership, current model/dimensions and application data on OpenAI-SDK.
Move managed memory from ClusterDemoTelco to mymemory without deleting the source.

## Observed baseline

- Engine CLI 0.1.120; memory status ready after cluster resume. Subsequent authenticated runtime readback confirmed v0.11.11; stored and received
  config generations are both 10. Received generation does not independently prove
  every effective setting inside the process.
- Source and destination MongoDB 9.0.4 replica sets; source M30_GEN_2, target M20.
- Source project database: 12 collections, 1,421 documents and 80 classic indexes
  at the recorded observation, plus 12 READY/queryable search/vector indexes.
- Collections include task queues, dead-letter queue, scheduling, extraction config,
  counters, snapshots and user context, in addition to memory types.
- Both workspaces reported zero reserved sessions. Background writer state is not
  established by this result.
- Destination authenticated connection passed; current credential sees no user
  databases. Full target ownership/visibility must be verified before restore.
- Installed Database Tools 100.11.0; current documentation explicitly supports
  MongoDB 9.0 in 100.20.0. No tool upgrade or transfer has been executed.

## Questions that determine an executable transfer

| Required answer | Why it matters | Evidence needed |
| --- | --- | --- |
| How are new memory writes blocked and all extraction/scheduled/in-progress tasks drained for the deployed Engine runtime? | Stopping interactive sessions does not stop background writes or TTL deletion | Supported maintenance commands and positive/negative drain checks; resume sequence |
| Is the complete project memory database the full transferable state, and which platform state must remain or move with it? | A data-only copier may omit queues, partitions or external configuration | Authoritative namespace/config boundary and version-specific restore requirements |
| How are original TTL, uniqueness, validators, partition definitions and search indexes preserved? | Counts alone cannot prove compatible memory or retrieval | Full metadata inventory and supported recreation/readiness checks |
| How is the project connection secret applied and the actual target attachment verified without changing the memory model/runtime version? | Secret presence and ready status do not identify the active database | Exact supported secret synchronization/restart and attachment verification procedure |
| What reverse transfer/reconciliation is supported after the first target write? | Switching back immediately can lose memories created on the destination | Post-write failure procedure, write freeze and reconciliation acceptance |

Do not replace these answers with an operator's assertion that migration is approved.
The joint-workspace approval is already recorded; the missing information is technical.

## Candidate copy mechanism and constraints

Prefer version-verified official Database Tools for an administrative full-database
transfer once consistency and Engine compatibility are established. Python may
orchestrate verified commands and compare metadata/results without becoming a
runtime memory owner. A permanent application bulk_write path is not introduced.

Official [mongorestore examples](https://www.mongodb.com/docs/database-tools/mongorestore/mongorestore-examples/)
describe documents, collection metadata/options and index definitions in dumps.
[mongodump](https://www.mongodb.com/docs/database-tools/mongodump/) states that a
live dump without oplog does not represent a single moment. Oplog-based backup is
not automatically a solution for a scoped project transfer: verify supported dump/
restore scope and privileges, and do not expand to unrelated cluster databases.
A dump does not capture writes after it finishes. TTL deletes must also be accounted
for when comparing source/target and preserving original expiry semantics.

The [Engine memory SDK configuration](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk-memory/)
documents changing enabled extraction types and applying configuration at restart.
It does not establish that disabling types drains existing queued work or halts
all writers. It also states existing search indexes are not rebuilt automatically
for changed partition keys. No extraction config change is proposed as a proven freeze.

## Execution boundary

After the missing procedure is verified, prepare the exact MM-1 role/network/index
proposal and isolated MM-2 rehearsal with bounded workload and rollback, then obtain
approval for the actual shared mutations under AGENTS.md. Do not change project
secrets, disable consumers, create broad credentials, restore/drop databases or
copy real memory into a test namespace before that proposal is concrete.

Until then, MM-0 is blocked on transfer compatibility and remains incomplete. This
review is a deliverable for unblocking the dependency, not a migration acceptance.

## Public API verification — 2026-11-02

Fetched the official OpenAPI document from the JSON link on the API documentation
page. Initial decoding failed because the downloaded response was gzip-compressed;
decoding its gzip bytes resolved the parsing error. [Schema evidence](../../compatibility/mm0-public-api-evidence.json)
records the inspected operations and constraints. The public memory API has config,
config sync, runtime status/provision/restart, retrieval and turn recording, but no
memory maintenance/stop/drain operation. Capacity has a minimum of one replica;
zero is not a documented shutdown mechanism. Tasks configuration exposes only
legacy_retry, which can terminalize backlog and is not a maintenance switch.

Performed two GETs for memory config/runtime with bounded responses and no redirects.
Sandbox requests failed with URLError; network-enabled requests returned 401.
Native `agentengine auth status` refreshed the private session, after which both
GETs passed. [Redacted readback](../../compatibility/mm0-engine-config-evidence.json)
records runtime v0.11.11/ready and config generation=received_generation=10. Only
field names, selected non-secret controls and a config hash were retained; no
prompts, credentials or private URLs were logged or committed.

The missing prerequisite is now specifically an operator-supported maintenance/
writer-drain and restoration procedure for this runtime. The absence of a public
endpoint does not prove an internal procedure does not exist. The requester was
asked for an internal reference or instructions; no support message was sent and
no shared configuration was changed. Do not replace this evidence gap with a
zero-replica setting, arbitrary role revocation or destructive retry configuration.
