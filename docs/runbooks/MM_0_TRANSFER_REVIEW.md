# MM-0: managed-memory transfer review

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

- Engine CLI 0.1.120; memory status ready after cluster resume. Runtime image/version
  still needs authoritative readback before selecting an operational procedure.
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
