# Current delivery status

Verified integration baseline: 2026-11-02. This index distinguishes current outcomes
from dated checkpoints in tasks and runbooks. Historical failures and unexecuted
checks remain evidence; their old pending-publication statements are not current gates.

## Integrated scope

| Track | Integrated result | Authoritative evidence |
| --- | --- | --- |
| Demo phases 0–8 | PR #4, `e524a57`; approved bounded demo | [Backlog](tasks/README.md), [OPS-001](tasks/OPS-001-RESILIENCE.md) |
| Profiles, multilingual and settings | PRs #5–15; UI-3 `3fa6fab`, LANG-3 `856bc60` | [UI-001](tasks/UI-001-PROFILES-CONTROL-PLANE.md), [I18N-001](tasks/I18N-001-MULTILINGUAL.md) |
| Tokenomics | PRs #16–19; TOK-3 `4b21bd6` | [TOK-001](tasks/TOK-001-TOKENOMICS.md) |
| UI-4 handoff | PR #20, `3fc9329fedb3ca1f5cc52ca24b1d236433e9d5a8` | [Clean-source handoff](runbooks/UI_4_HANDOFF.md) |
| Development memory/store cutover | PR #21, `bfb52efde401b3a91f6a086cc886b8051fab08e5` | [Applied cutover](runbooks/MM_DEV_CUTOVER.md), [ADR-0031](adr/0031-mymemory-target.md) |

UI-4 source `c5a48ffb9ee874d9868a638095195f03bdcd1bf6` passed CI
[41377374537](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41377374537)
and [41377398573](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41377398573).
MEM-002 source `6269f20a5c608620340a5cd9b712172c5871d6c4` passed CI
[41446494091](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41446494091)
and [41446509299](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/41446509299):
75 compatibility, 15 identity, 322 backend, 96 hosted-contract, 11 frontend unit and
36 browser tests (555 total), plus repository checks, lint, types and builds.
These are CI contracts, not new live provider acceptance.

## Applied development topology

OpenAI-SDK retains application, identity, knowledge, evaluation and load data.
Engine uses mymemory for its project-managed memory and store/checkpoints; both
agentsdk and geo-intelligence-network deployments were synchronized. ClusterDemoTelco
remains intact as the historical source. Runtime access is restricted to the two
project databases and the mymemory cluster; the administrative credential is not
installed in Engine.

Old memory was intentionally not copied under the accepted development memory-loss
override. The store copy restored 14,951 documents in 33 collections with 116 classic
indexes and zero restore failures. It was a best-effort copy without an oplog snapshot.
Engine memory is ready; 12 search/vector indexes are queryable. Two native writes,
three context reads, owner isolation, target/source placement and denied unrelated
database access passed. The initial sync/readiness failure and its dependency/role
correction remain in the [execution record](runbooks/MM_DEV_CUTOVER.md).

## Remaining limits and follow-up

- [SEC-001](tasks/guardrails_avoid_prompt_injection.md) is the planned prompt-injection assurance track, restricted to agentsdk-only guardrails, approval, egress and application gap fixes. Shared project/organization policies are read-only; Geo changes are excluded. Existing tests establish narrow controls; broader indirect/multi-turn evidence remains open. The plan does not resume app testing.

- Lossless migration and rollback design remain future product review; the accepted
  development cutover is complete. No full hosted chat/voice evaluation was rerun
  after this cutover, and retained source data does not guarantee lossless rollback.
- Tokenomics uses explicit estimates and partial coverage with accepted trailing
  7/30/90-day periods. No actual billing or custom historical range is claimed.
  Rates use the selected [OpenAI](https://developers.openai.com/api/docs/pricing)
  and [Anthropic](https://platform.claude.com/docs/en/about-claude/pricing) sources;
  missing usage and prices remain unavailable.
- Quiet-environment voice and the incomplete nine-case language matrix remain
  accepted demo limitations. Production capacity and pricing proof were excluded.
- The development lint dependency chain retains the documented moderate minimatch
  advisory; runtime audit was clear at UI-4 acceptance.
- The local Python 3.15.2 environment has a missing `encodings` standard-library
  failure. Repair it before new local application validation; do not downgrade the
  target. The clean CI results above do not repair that local environment.
- Merge does not deploy or restart local servers. Preserve private activation and
  credential-version requirements in [AGENTS.md](../AGENTS.md). The USD 30 provider
  ceiling remains unchanged.

## Delivery workflow

The requester authorizes scoped commits, pushes, PRs and automatic merge after
required quality/CI gates. Historical manual-publication instructions are superseded.
No further user decision is pending for the completed development cutover. New shared
Atlas changes still require an exact authorized scope; this documentation closure
performs no new Atlas, Engine, provider or application-runtime operations.
