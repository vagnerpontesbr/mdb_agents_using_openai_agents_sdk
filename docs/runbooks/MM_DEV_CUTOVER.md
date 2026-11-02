# Dev-only mymemory destination switch

## Result

The dev cutover passed. Engine memory and the managed project store now use mymemory.
Both deployments synchronized successfully; memory runtime v0.11.11 reports ready.
[Sanitized execution evidence](../../compatibility/mm-dev-cutover-evidence.json) records
roles, copy results, native write/read checks, indexes and the corrected failures.

## Decision and scope

On 2026-11-02 the requester accepted memory loss in preview/development and moving
agentsdk and geo-intelligence-network together. This supersedes the historical
preservation-first blocker for this switch. [ADR-0031](../adr/0031-mymemory-target.md)
and [MEM-002](../tasks/MEM-002-MYMEMORY-MIGRATION.md) own scope. No historical memory
records are copied and ClusterDemoTelco is retained. The application stays on
OpenAI-SDK; Engine remains the sole runtime memory writer.

The requester replied "continuar" after the [exact scoped-user proposal](../../compatibility/mm-dev-cutover-proposal.json).
The supplied mymemory administrative credential had atlasAdmin and no cluster scope;
it was not installed in the runtime. A new SCRAM user engine_memory_devmove_20261102
was created with readWrite and dbAdmin only on mdb_memory_67b385a7976edf15ecc62e06,
restricted to the mymemory cluster. Atlas readback matched the proposal exactly.
The randomly generated password is retained only in private configuration and the
Engine secret store. It was submitted via stdin, never a command-line argument.

## Execution checkpoint

- Atlas source, application and target were IDLE/unpaused before cutover. Both
  workspaces reported zero reserved sessions; no session cancellation was needed.
- New credential ping/authentication passed. Reading telecom_identity.users was
  denied with code 13. The target memory database initially had no collections.
- Existing project MONGODB_URI was version 1. Native secret set through stdin
  succeeded as version 2 at 2026-11-02T12:15:12Z.
- Native project secret sync started; completion and actual target attachment are
  separate gates. Runtime readiness alone does not establish the destination.
- Config generation and received_generation remained 10, with unchanged config hash
  a6d08f6efd12cfc7edbb494bf68b7594cd98f82be5739cdb68561fd32748aece.
  Memory image remained v0.11.11. No model/dimension or extraction change was made.

The live write/read and target-storage gates are pending at this checkpoint. Do not
claim completion or old-memory continuity based only on the updated secret.

## Rollback and accepted limits

Source data and existing administrative users are not deleted. The local MONGODB_URI
points to OpenAI-SDK, so it cannot restore the previous Engine source configuration.
Returning to the old destination requires its verified private connection; new target
memories would not be reconciled automatically. Data loss is accepted for this dev
scope, not a promise of zero-loss rollback or production migration support.

## Runtime failure and newly identified store dependency

Project secret sync timed out after five minutes: values were stored but the next
message might still use the previous generation. Ran `agentengine memory apply`
with --wait and no upgrade. Engine created 12 target collections and 12 READY/queryable
search/vector indexes under the restricted identity. Memory configuration/image stayed
unchanged. However, readiness then reported failed, blocked_on orchestration_engine;
secret-runtime readiness reported broker/pending. No canary writes were issued.

Source metadata subsequently confirmed a companion mdb_store project database.
Official LangGraph SDK documentation states the MONGODB_URI connection also serves
checkpointer/query storage, with a project-scoped mdb_store base name. This dependency
was missing from the original memory-only identity proposal. Runtime authorization
failure on the companion store is a supported hypothesis, not a confirmed internal
log diagnosis; public memory-runtime status provides no detailed message.

[Proposed store-scope correction](../../compatibility/mm-dev-store-scope-proposal.json)
adds readWrite/dbAdmin only on that project's mdb_store database, keeping the same
mymemory cluster restriction. It also implies a fresh development checkpoint/store
state, not just empty semantic memory, so explicit approval is needed before expanding
the grant. The old memory and store databases are retained. No broader role was granted.
The cutover is incomplete and the shared Engine runtime is not healthy at this checkpoint.

## Store dependency correction and final verification

The requester authorized copying all dependencies after the missing project-store
scope was explained. The destination store was verified empty. Official macOS ARM64
Database Tools 100.20.0 were downloaded from fastdl.mongodb.org; archive SHA-256:
12d02963f6d17aa16de0919af61c8dd6dc30921439e665c432fb0afeeb8c8f23.
Both binaries reported 100.20.0. A private scoped mongodump of mdb_store was restored
with mongorestore --nsInclude, --stopOnError and one collection worker. No --drop or
source write was used. **14,951 documents restored; zero failures**, including managed
state/checkpoint dependencies across the 33 observed source collections. This was a
dev best-effort copy without oplog, not a guaranteed consistent snapshot.

The runtime user retained its mymemory-only cluster scope and received readWrite/
dbAdmin only on this project's mdb_store as well as mdb_memory. Readback matched.
The supplied atlasAdmin credential was used only by the administrative restore;
it was not installed in Engine. Temporary plaintext credential files were removed.
Existing source credentials/users and databases were not modified.

After this correction, the second `agentengine secret sync --project-scope` succeeded
for **two deployments, zero skipped**. Native memory status and the runtime API then
reported ready; image and config hash/generation were unchanged. This is the rerun
result for the earlier timeout/failure, not an erasure of those failures.

Native canary helper issued exactly two POST /memory/turns (HTTP 201) and three
POST /memory/context (HTTP 200): each owner retrieved its marker; the other user
received no marker or memory. Direct target counts returned one record per canary;
the same exact-user query on the source returned zero. The write path was Engine,
not an application copier. Retrieval metadata reports embedding work; no business
agent was invoked and no exact provider charge is claimed. The target has 12 READY/
queryable search/vector indexes. Its 77 classic bootstrap indexes differ from the
source's historical 80; this fresh memory initialization does not claim cloning old
custom indexes. Scoped access to telecom_identity was denied (code 13). Final
application credential ping/authentication on OpenAI-SDK passed.

The Control Plane no longer hard-codes that migration is planned. Its three-language
text states that the destination is configured in Agent Engine; it does not present
static text as a live health probe. No existing local application server was restarted.

## Local and publication checks

Executed frontend lint, typecheck, 11 unit tests and build; all passed. Repository
link/ADR checks and git diff --check passed. Full local Python/browser suites were
not rerun: the earlier local Python 3.15.2 standard-library failure remains unresolved.
Remote CI must run those suites on the publication commit. No new full hosted chat/
voice evaluation or production-capacity claim is part of this dev cutover.

Final metadata verification: the copied store has **33 collections and 116 classic
indexes**, matching the source inventory; the source store has no search indexes to
recreate. The runtime credential still receives code 13 outside its two authorized
databases after the store grant. The private temporary dump/log directory was removed
after verification; the original cluster remains the retained recovery source.
