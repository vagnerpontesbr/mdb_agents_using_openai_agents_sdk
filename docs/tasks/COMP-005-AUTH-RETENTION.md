# COMP-005: Requester authorization and memory retention contract

- Status: Requester authorization pending; native expurgo accepted by user without further proof
- Owner: Repository implementation
- Dependency: COMP-002, COMP-003
- Authoritative policy: [ADR-0019](../adr/0019-requester-approval-memory-retention.md)

## Bounded deliverable

Identify a supported Engine contract for the selected policy without changing shared settings. This checkpoint is contract inspection, not deployment or a successful authorization/deletion test.

## Evidence: 2026-10-29

Inspected installed `agent-engine-sdk==0.11.11` and `agent-engine-sdk-memory==0.11.11` in the existing hosted compatibility environment. `RequestContext` exposes `user_id`, `request_headers`, execution/session/workspace identity and resume data, but no separately typed authenticated approver principal. The existing review activity binds `requesting_user_id` to its semantic action. Earlier CLI evidence accepted a delegated synthetic user ID; equality of that value is not an independent authentication proof. Headers may provide a supported route, but their trusted provenance and identity contract have not been validated.

The installed memory client exposes `delete_procedural`, requiring an owner `user_id` and defaulting to `soft=True`. This is not a complete user/session/source-and-derived deletion contract. A source scan of the installed SDK and memory package found no `ttl_days` or retention configuration surface. This narrow result does not establish absence of a platform API.

The official [Engine API reference](https://www.mongodb.com/docs/api/doc/agentengine), retrieved through MongoDB knowledge search, documents `memoryconfig.SnapshotConfig.ttl_days` and `delete_promoted`. It does not establish from the returned contract that the setting covers all memory types or isolates one workspace. The [memory SDK documentation](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk-memory/) states that memory is project-scoped. No project configuration, TTL index, memory record, credential or deployment was changed.

## Acceptance controls still required

1. Identify and validate the trusted principal supplied by Engine or the authenticated backend. A separately authenticated requester can approve; another user and a spoofed requester cannot. Denial must occur before decision acceptance/business release, and must leave the request available to its owner.
2. Verify supported per-application retention and deletion coverage for STM, snapshots and each derived memory type. Establish timestamp origin, asynchronous deletion delay, task cancellation/regeneration behavior and isolation from the other application.
3. Use a supported isolated synthetic expiry fixture; verify records before expiry, then deletion and absence from all retrieval paths. Never backdate or remove existing shared records directly to force a pass.
4. Keep the combined approval-timeout/memory test separate from the thirty-day retention test.

## Next steps and limits

Continue read-only platform contract investigation and independent compatibility work. A second identity is an execution prerequisite for the authorization negative control, not a requirement for a separate human reviewer. No additional business policy decision is requested at this checkpoint. If only project-wide retention is supported, present the concrete isolation alternatives before changing topology or shared settings. Phase 0 remains incomplete.


## Complete public API and header provenance inspection

The public [OpenAPI JSON](https://www.mongodb.com/docs/api/doc/agentengine.json) was fetched on 2026-10-29. [Portable contract evidence](../../compatibility/auth-retention-contract-evidence.json) records its decompressed SHA-256, exact relevant schemas/routes and hashes of the inspected local 0.11.11 package files. This supersedes the earlier search-snippet-only scope.

The memory config PUT explicitly stores project-level settings. The captured specification contains no workspace-scoped memory configuration route and no DELETE memory operation. Snapshot `ttl_days` and `delete_promoted` still do not document retention of every derived type or an application-specific deletion boundary. This is a limitation of the captured public contract, not a claim that no other Engine interface exists. Moving to another project alone would not prove complete deletion coverage.

The public execution resume operation requires Bearer authentication and exposes `suspend_generation` to reject decisions against changed suspension content. It does not document requester-only approval. This endpoint's decision schema is distinct from the currently tested native interrupt resume-map flow; do not substitute one for the other without a compatibility test.

Pinned `InvokeRequest.custom_headers` is explicitly caller-provided: `X-Mdb-Agent-Engine-Custom-*` headers are forwarded with the prefix stripped. AER copies them directly into `RequestContext.request_headers`. Consequently, an asserted requester header is not a safe authorization mechanism. The earlier suggestion that headers might supply identity now specifically requires independent authentication/signature verification, not string comparison. No such mechanism is implemented or claimed here.

The next executable authorization control requires a verified authentication boundary and two independent principals. Full thirty-day enforcement requires a supported scoped lifecycle contract; a global TTL or direct managed-database cleanup is not an authorized fallback. Other Phase 0 compatibility work can continue independently. No credentialed operation, model call, deployment, configuration change or deletion was performed in this inspection.


## Live native expiry inspection: 2026-10-29

Read-only PyMongo 4.19.0 inspection used the existing ClusterDemoTelco MCP connection configuration to obtain full index options omitted by the MCP index-summary tool. [Index evidence](../../compatibility/native-retention-index-evidence.json) records all ten inspected collections. No memory content or secrets were returned.

- `memory_snapshot` has `snap_ttl` on `expires_at`, with `expireAfterSeconds=0` and no partial filter. This is a collection-wide native expiration mechanism based on each record's timestamp, not a workspace-specific index.
- The original synthetic hosted session's snapshot has `ttl_days=30`, timestamp `2026-10-29T13:00:28.193Z` and `expires_at=2026-11-28T13:00:28.194Z`. [Scoped MCP evidence](../../compatibility/native-retention-snapshot-evidence.json) confirms the existing stored record; no setting was changed. This establishes configured thirty-day expiry for this snapshot, not physical deletion, whose deadline is still in the future.
- No TTL indexes were present in `memory_short_term`, `memory_semantic`, `memory_episodic`, `memory_procedural`, `memory_taxonomic` or `memory_user_context`. Absence of TTL indexes does not rule out Engine task-based cleanup, and snapshot deletion does not establish a cascade to these collections.
- Infrastructure `tasks` expire 172800 seconds (2 days) after `expires_at`; `tasks_dlq` expire 5184000 seconds (60 days) after `moved_to_dlq_at`. `scheduled_tasks` has no TTL index. These are not evidence of conversation retention.

The current Engine config GET returned HTTP 401 with the locally configured token. Consequently, current `delete_promoted` and project-wide runtime settings remain unverified; this is distinct from the successful MongoDB reads. The inspected `extraction_config` collection returned no metadata samples and did not provide an alternate configuration source.

[MongoDB TTL documentation](https://www.mongodb.com/docs/manual/core/index-ttl/) describes automatic background deletion, generally checked every 60 seconds, with potentially longer delays under load. A TTL index does not guarantee deletion at the exact deadline. The live evidence therefore confirms the native snapshot expiry mechanism and an existing thirty-day record, while complete source/derived expurgo and actual future deletion remain separate gates. No direct managed-memory write, index modification, deployment or project configuration change occurred.


## Official guide review: 2026-10-29

Read the rendered MongoDB guides directly, following the Agent Engine documentation navigation, rather than relying only on OpenAPI search excerpts:

- [Add Memory to Your Agent](https://www.mongodb.com/docs/agentengine/add-features/memory/) explicitly states that all agents in a project share the memory service, store and settings. Its configuration/defaults example contains `background_extraction.snapshot.ttl_days: 30` and `delete_promoted: false`. This corroborates the live snapshot observation, but is not a guarantee that all memory types expire. The guide does not define a complete cascade-deletion contract for those settings. Updating configuration uses `memory configure` then `memory apply`; apply restarts the memory server and does not require agent redeployment.
- [Memory Extraction](https://www.mongodb.com/docs/agentengine/add-features/memory-extraction/) defines separate turn, snapshot, extraction and reconciliation stages. Reconciliation uses ADD, UPDATE (a new version supersedes the previous version), and REINFORCE (strengthens existing memory). It preserves learning/reinforcement history; reconciliation is not a documented timed purge. Disabling an extraction type only stops future automatic extraction, not existing-memory deletion.
- [Agent Memory](https://www.mongodb.com/docs/agentengine/add-features/memory-types/) describes STM as chronological raw turns and long-term memory as knowledge persisting across sessions. Taxonomic knowledge is project-shared. [SDK capability matrix](https://www.mongodb.com/docs/agentengine/sdk/python/packages/agent-engine-sdk-memory/docs/capability-matrix/) further states that consolidated episodic memories have `session_id: null`; session-based cleanup cannot be assumed to find all derivatives. Documentation describes chronological storage, not validated full-history restoration in the custom OpenAI adapter.
- [Human-in-the-Loop](https://www.mongodb.com/docs/agentengine/deploy/human-in-the-loop/) documents allowed-decision validation and native suspend/review/resume. It does not establish the selected requester-only domain rule. Custom headers are not persisted across suspension and must be resent; they remain caller input, not proof of authentication.
- [Service accounts](https://www.mongodb.com/docs/agentengine/api-keys-service-accounts/) documents access-token lifetime as one hour. A token must be minted again using the existing client credentials. The prior HTTP 401 may reflect expiry; its precise cause was not verified. It does not imply a missing memory feature or a failed MongoDB connection.
- [Public Preview Limitations](https://www.mongodb.com/docs/agentengine/reference/limitations/#security) explicitly distinguishes project agent isolation from API authentication: agents share an OE, and OE does not authenticate/authorize calling agents. This is not a claim that public API calls lack authentication. Workspace registration alone is not a security boundary between applications.

Conclusion: snapshot expiry is documented and configured for the observed synthetic record. Full thirty-day deletion of raw turns and every derived/versioned memory is not established by the reviewed guides. Keep that acceptance gate open without describing native expiry as absent. Recover the existing service-account token to inspect current settings; do not rotate shared secrets or change settings simply to work around the HTTP 401. Requester authorization remains a backend domain check integrated with Engine-owned approval, and requires independent identity controls.


## Refreshed-token configuration read passes

After the user refreshed the existing service-account token on 2026-10-29, the config GET returned HTTP 200. [Sanitized configuration evidence](../../compatibility/native-retention-config-evidence.json) records generation 10 and received_generation 10, resolving the earlier HTTP 401 blocker for this read. A preceding read using the existing CLI session independently returned the same settings, and the CLI memory status reported ready. No CLI credential was copied into application configuration.

The stored snapshot configuration explicitly sets `max_messages=20` and `stale_minutes=1`. It does not explicitly override `ttl_days` or `delete_promoted`. The official guide's defaults are 30 and false respectively; the previously inspected synthetic snapshot independently confirms an actual thirty-day expiry. Do not claim the API returned those omitted defaults or that received_generation alone proves every effective runtime value. Enabled extraction types are semantic, episodic and taxonomic; short-term embed-on-write is true.

This completes the read-only configuration/delivery inspection. The thirty-day requirement is supported for the observed snapshot; automatic source-turn removal and all derived-memory/version deletion remain unproved. There is no explicit all-memory expiry policy in the returned configuration. No config PUT, apply/restart, deletion or deployment was performed, and the current shared memory settings were preserved. The remaining lifecycle gap now concerns documented coverage and behavior, not access to the configuration endpoint.


## User acceptance of native expurgo

The latest user instruction accepts expurgo as Agent Engine responsibility and removes the requirement to prove it in this asset. The earlier expurgo/cascade/retention tests are no longer Phase 0 gates; see the [ADR acceptance adjustment](../adr/0019-requester-approval-memory-retention.md#acceptance-adjustment-selected-by-the-user). No additional shared configuration change or successful full-coverage deletion test is implied. Remaining COMP-005 work is authenticated requester approval and denied other-user/spoofed-requester controls.
