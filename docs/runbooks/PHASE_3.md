# Phase 3: Memory continuity and recovery

Historical phase-specific evidence and versions follow. Use [Phase 7](PHASE_7.md)
for the active runtime and [publication status](REPOSITORY_SETUP.md) for current Git/CI.

[MEM-001](../tasks/MEM-001-MEMORY.md) is the authoritative acceptance record.
Phase 3 passed for the bounded demo. Active build: `bld_01M6646NXQBCED02KMERQE601M`;
deployment: `deploy-aada0f7f` (succeeded). Manual Git publication remains pending.
Use the existing [application startup](APPLICATION.md) and enable the journey
as described in [Phase 2](PHASE_2.md). Engine remains the only memory and execution
owner. This phase adds no database, collection, role or shared policy setting.

## Reproduce continuity with synthetic accounts

1. Sign in as the demo administrator and create two synthetic `user` accounts.
   Keep their passwords in private injected configuration, never fixtures or logs.
2. Sign in as the first user and send: “For future comparisons, my preferred home
   internet plan is fiber-500. Please compare fiber-500 now without making any
   change.” The response must use the current synthetic tool price, USD 89.90.
3. Allow native asynchronous extraction to finish. A successful turn is not proof
   of immediate semantic availability. Do not write duplicate memory records or
   change shared snapshot settings to force the test.
4. Choose **New conversation** and ask: “Compare my preferred home internet plan
   using current pricing. If you do not know my preference, ask me which plan.
   Do not propose a change.” The positive control requires the current fiber-500
   offer through the sales tool, without a proposal or simulation.
5. Ask the identical question as the second user, without seeding a preference.
   Expect a request for clarification and no inferred first-user preference.
   Require the positive control before accepting the negative as isolation proof.
6. Inspect Engine traces for the exact user/session/execution. Confirm private
   semantic/episodic context, successful source metadata, current tool output,
   and no second memory writer. Keep raw private memory out of exported evidence.

These controls demonstrate same-project authenticated application-user isolation.
They do not prove isolation across independent organizations/projects, retrieval
quality on a corpus, exact transcript restoration, or immediate availability.

## Recover an execution

Reload the page: the application reads the native latest execution for the saved
opaque conversation UUID. **Check latest execution** repeats that read on demand.
For a pending proposal, verify the exact plan and price before approval. Only the
requester can approve; being an administrator does not override that boundary.

Stopping browser waiting does not cancel Engine work. After uncertain transport,
sending and starting a new conversation remain disabled until a newer native
execution is recovered. An empty lookup or a preceding completed execution does
not establish the uncertain request's outcome. Resolve a persistent uncertain
case against Engine status before restarting manually; do not clear browser
storage merely to bypass the warning.

The saved UUID and temporary predecessor execution reference contain no transcript
or approval state. Closing the tab may remove them. Cross-device discovery of
unfinished conversations is outside the bounded demo.

For a runtime restart test, stop only the explicitly identified synthetic runtime
session through the native API, wait until it is absent, then recover its pending
execution through the authenticated application and approve it. Confirm no
additional model calls and exactly one simulation tool success. Never stop all
workspace sessions or infer that stopping a runtime deletes its memory/history.

## Deployment and publication

Prepare a fresh credential-free journey stage using the command in Phase 2.
The Phase 3 workflow adapter version is 4; changes to its prompt and context inputs
must not be assumed replay-compatible with older suspended executions. Complete
or explicitly resolve owned test executions before deploying a new adapter.
Keep the existing model, tool allowlist, memory configuration and credentials.

Record exact build/deployment IDs and source hashes in the task evidence, because
generic latest-deployment status has returned stale results. At acceptance, stop
at the Phase 3 boundary and provide manual commit/push commands. Phase 4 requires
a new user confirmation.
