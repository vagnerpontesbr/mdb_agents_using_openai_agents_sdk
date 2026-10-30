# MEM-001: Semantic continuity and native execution recovery

- Status: Complete for the bounded demo; manual publication pending
- Scope: Phase 3, authorized after Phase 2 publication
- Decisions: [ADR-0021](../adr/0021-demo-semantic-episodic-continuity.md),
  [ADR-0018](../adr/0018-engine-feature-precedence.md),
  [ADR-0019](../adr/0019-requester-approval-memory-retention.md)

## Acceptance criteria

1. Retrieve private semantic/episodic context once per journey through Engine,
   bound to the authenticated Engine execution user. Share that same historical
   data with the supervisor and invoked specialists, preserving the current user
   request verbatim. Do not create another memory writer or SDK Session store.
2. Demonstrate a remembered preference in another conversation with current
   synthetic tool facts, and a different authenticated user's negative control.
   Same-project application-user isolation is not independent organization or
   project tenancy. Full chronological history and immediate extraction are not
   promised; native thirty-day expurgo remains accepted without another proof.
3. Recover the latest native execution after reload/restart, including pending
   review. Deny wrong user and wrong conversation access. Preserve native
   generation checks, replay ownership and same-session concurrency protection.
4. Block accidental browser resubmission after uncertain transport. An empty
   lookup or the preceding execution cannot resolve a newer uncertain request.
   Starting another conversation must not bypass recovery or a pending review.

## Implementation

The Phase 2 journey supplied memory to the supervisor but discarded it at
specialist delegation. The corrected bridge retrieves once and supplies the same
JSON data envelope to each invoked specialist. Current request text is preserved;
model-generated summaries cannot replace it. Fixed memory trust instructions
apply to every model call. Current amounts and proposals still come from domain
tools and exact response templates. Transport tests are not proof of general
prompt-injection resistance or memory retrieval quality.

`retrieve_context` also compares the supplied user with the Engine execution's
current user before retrieval. Existing organization/project/workspace, execution
and session checks, private visibility, semantic/episodic sources, hybrid mode,
2,048-token budget and fail-closed source metadata checks remain in force.
Workflow adapter version 4 identifies the changed model input contract. Do not
assume old suspended version-2/3 executions can migrate to it.

The browser automatically reads the native latest execution on entry and offers
**New conversation** after recovery/completion. sessionStorage retains the opaque
conversation UUID and, only while an invocation is uncertain, its predecessor
execution ID (or an empty predecessor marker). These are recovery references,
not stored messages, approvals or an execution database. Reload retains the
recovery requirement. Closing the tab clears these browser references; selected
Engine memories can remain available in a new conversation. This is not
cross-device discovery of unfinished conversations or full transcript restoration.
A definitively rejected invocation without a new Engine execution can require
operator diagnosis; the UI does not invent a successful outcome to unlock it.

## Reused evidence

- [Phase 0 hosted recall](COMP-003-HOSTED.md#hosted-model-memory-recall-passes)
  proves the earlier bounded same-user/new-session semantic recall path.
- [Phase 2](VERT-001-JOURNEY.md) proves native restart-before-approval,
  generation conflicts, expiry/rejection, no repeated model calls on replay,
  and overlapping same-session invocation conflict. These are bounded controls,
  not capacity or generic exactly-once business guarantees.
- Phase 2 commit `3c68530d932182b0fdba81319dc08a5a4dfb841d` has successful
  [remote CI](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41036233739).

## Local validation

- 82 hosted contract tests passed on macOS Python 3.15.2, including shared memory
  input, current tool price overriding historical text, and wrong-user rejection.
- 45 backend tests passed, including independently authenticated users sharing a
  conversation UUID, wrong-session recovery, and recreated service recovery.
- Nine Chromium tests passed, including reload with pending approval, new
  conversation, and empty/old recovery results after uncertain transport.
- Frontend build/typecheck/lint and backend Ruff/mypy passed.
- The first expanded browser suite hit the real sign-in rate limit. Journey tests
  now reuse their own synthetic session; application limits were not changed.

These deterministic checks use provider doubles. The final hosted acceptance below
separately establishes the bounded real-provider behavior.
Changes are locally authored; no Phase 3 commit, push or remote CI is claimed.

## First hosted iteration and correction

Build `bld_01M663PKHWRDGW7P6S2QGR8MHX`, deployment `deploy-c0439f67`,
completed successfully at 2026-10-30T09:58:56.023Z. Two synthetic application
users were registered through an authenticated administrator using the restricted
Atlas identity connection. Subsequent live controls used actual password login,
SessionAuth and JourneyService, with the private backend Engine CLI credential.
No identity facade was substituted in these Phase 3 controls.

The first user seeded a fiber-500 preference through the normal hosted journey.
Native extraction later returned one selected semantic and one episodic record;
the second user's context was empty, with no source degradation. An initial
empty read was observed before extraction, without repeated memory writes.
However, the first new-session journey returned clarification even though its
trace included the preference. This iteration does not pass end-to-end recall.
The next prompt revision explicitly permits historical preference data to resolve
an informational comparison while keeping current choices authoritative and
requiring current tool facts. It does not permit historical approval to authorize
a new action. The model remains gpt-5.6-luna.

The [official OpenAI prompt guidance](https://developers.openai.com/api/docs/guides/prompt-engineering)
was consulted for explicit instructions, separated context and behavior evaluation.
Prompt wording is not an authorization boundary or a guarantee of model behavior.

Live recovery passed after the seed runtime stopped, including a recreated
backend service, another user's denied execution read, and an empty lookup for
that other user using the same conversation UUID. A separate pending proposal
was recovered after its runtime was confirmed absent; the other authenticated
user was denied approval, and the requester resumed successfully. Its native
trace has three successful model calls, one offer and one simulation tool success,
with no additional model calls on replay.

Reproduction steps and browser-reference limitations are in the
[Phase 3 runbook](../runbooks/PHASE_3.md). The final prompt/deployment acceptance below supersedes that failed iteration;
its earlier successful controls alone did not make the recall gate pass.

## Final Phase 3 checkpoint

Build `bld_01M6646NXQBCED02KMERQE601M` deployed successfully as
`deploy-aada0f7f` at 2026-10-30T10:07:56.012Z, with all components healthy.
The staged source files match the locally authored source hashes in
[portable evidence](../../compatibility/phase3-memory-evidence.json).

- Same authenticated user, new conversation: the unchanged preference question
  returned the current fiber-500 offer at USD 89.90 through the sales tool.
  The question did not repeat the plan ID. No proposal or simulation occurred.
- Other authenticated user, identical question: `needs_information`, with no
  business tool call. Public plan names in the generic clarification are not
  a claim about that user's preference. Independent context retrieval was empty.
- Final-version pending proposal: runtime confirmed absent before recovery;
  the exact action was recovered, the other user was denied approval, and the
  requester completed it. Trace: three model successes, one offer and one
  simulation success; no repeated model calls on resume. One memory success
  remains correlated to the execution, without a separate application writer.
- Trace results were not truncated and matched their exact session scopes.
  Phase 2 same-session concurrency, stale-generation and expiry controls are
  reused because those native/domain mechanisms did not change in this phase.

The 82 hosted tests also passed with current source on Linux/amd64 and network
access disabled. Frontend unit tests (3), Python package build, repository checks
and configured-credential scan passed. The initial Linux command named an absent
`python` executable; rerunning with the image's actual `/app/.venv/bin/python`
and source mounted at `/app/src` passed. This is a reused locked image, not a
fresh dependency installation. Native test sessions were stopped selectively;
the two synthetic non-admin test accounts remain in the application identity store.

Phase 3 is complete within ADR-0021's semantic/episodic demo scope. No shared
memory policy, provider credential, database privilege or tool allowlist changed.
The final hosted build is deployed, but these local source/docs are not committed
or pushed. Stop here for the user's manual publication; do not start Phase 4.
