# VERT-001/002: Authenticated telecom journey

- Status: Phase 2 complete for the bounded demo; locally authored and Engine-deployed, manual commit/push pending
- Owner: Repository implementation
- Phase: 2
- Dependencies: Published Phase 1 and accepted bounded Phase 0
- Decision: [ADR-0025](../adr/0025-phase-two-journey.md)
- Operational steps: [Phase 2 runbook](../runbooks/PHASE_2.md)

## Scope and acceptance

The user explicitly authorized Phase 2 after committing Phase 1. Deliver a real
SDK supervisor and financial/technical/sales specialists with synthetic tools,
authenticated chat, browser voice, Engine-native review and bounded failure paths.
Complete local checks and credentialed hosted acceptance before calling the phase
complete. Pure approved simulation receipts do not represent live plan changes.

## Authored implementation

`compatibility/openai_engine_adapter/src/openai_engine_adapter/journey_domain.py`
contains typed synthetic inputs/results and exact critical text. `journey_agent.py`
uses the SDK Runner and agents-as-tools through Engine proxies. `journey.py` adds
the durable hosted entrypoint, native review/deadline and four remote tools.

`src/telecom_app/journey.py` admits authenticated users to native executions and
checks exact review/scope/generation. `voice.py` supplies bounded SDK speech stages;
`api.py`, `config.py` and `security.py` expose the protected endpoints and body bounds.
`apps/web/src/Journey.tsx`, `recording.ts` and the worklet supply the browser path.
The root lock adds the pinned voice dependency set. The staging script supports an
explicit journey profile; CI adds the hosted-contract suite using the adapter lock.

## Validation evidence (2026-10-29 local / 2026-10-30 UTC)

| Check | Result and scope |
| --- | --- |
| Root dependency sync | Passed with Python 3.15.2; pinned OpenAI SDK/voice dependencies installed and uv.lock updated |
| Backend Ruff / strict mypy | Passed; 11 application modules typed |
| Foundation/HTTP tests | 42 passed, including signature-checked STT/TTS stages and no automatic speech retry |
| Hosted SDK contracts | 76 passed on macOS ARM64 and Linux amd64; 15 new journey/review controls, real Runner/AER with doubled Engine transport |
| Frontend lint/types/unit/build | Passed; 3 existing unit tests; worklet emitted as a separate same-origin asset |
| Playwright | 6 passed: identity, mobile, proposal approval/rejection, uncertain-result recovery, microphone denial; journey provider responses are doubles |
| Visual inspection | Desktop proposal and mobile completed-result captures reviewed; percentage row-gap/footer overlap corrected and final browser rerun passed |
| Final repository checks | 67 Markdown files/25 ADRs passed; git diff --check passed; no configured private credential value found in versionable files |
| Wheel/sdist | Root package built with the pinned build toolchain |
| Identity regression | 15 passed; requester-only admission and existing login policy |
| Linux dependency resolution | Root frozen lock installed successfully on Linux amd64/Python 3.15.2, including the added voice dependencies |
| Compatibility regression | 75 passed, including the new journey staging manifest test; socket tests required normal local socket permission |
| Live read-only Engine connection | Status/policy reads succeeded; project allowlist lacks all four new tools; Policy expansion applied after user authorization; deployment started |
| Hosted stage | Credential-free journey source and verified compact Python bundle uploaded as build bld_01M658HJQT43486QV3XTN17D0K; build succeeded at 2026-10-30T02:02:26.009Z, not deployed |

## Pending gates and limitations

The exact shared-policy expansion and required live matrix are recorded once in
the [runbook](../runbooks/PHASE_2.md). Generic resume-to-custom-review mapping, new
Tool Pod user propagation, managed memory projection/replay under the multi-agent
sequence, live routing and complete browser voice are not proven by local tests.
The journey is disabled by default pending deployment acceptance.

No Phase 2 commit, push, PR, remote CI or deployment is claimed. Phase 1 publication
was verified separately: commit `b2ff9c7`, PR #2 merged as
`f7611dc7571aef4d76da0c6f8d6069ef85ebd146`, passing
[main CI](https://github.com/vagnerpontesbr/mdb_agents_using_openai_agents_sdk/actions/runs/40986600069).
The current Phase 2 branch is `codex/phase-2-journey`, created from the Phase 1
commit; local main was not silently reset or remote history rewritten.

[Portable evidence and uploaded source hashes](../../compatibility/phase2-journey-evidence.json)
identify the staged artifact independently of Git metadata. The stage intentionally
contains no Git directory and the build therefore has no commit SHA.

## Authorized rollout and first live controls (2026-10-30)

The user approved the four named shared-tool additions. A fresh policy read,
append-only update and read-back verified 27 → 31 authorized tools and unchanged
other policies. The private CLI login was refreshed without exposing credentials.
Deployment `deploy-c4c7b79d` succeeded at 02:13:40.784Z after a transient Engine
`CertificatesReadyNotReady` condition. A probe sent during rollout still reached
the prior recall contract; that old execution was subsequently cancelled and is
not Phase 2 evidence.

The new deployment completed real financial, technical and mixed requests. The
mixed response consulted all three specialists and returned the exact synthetic
invoice, network and offer text with matching user scope. The initial explicit
plan-proposal request returned `needs_information` incorrectly: the trace showed
the supervisor inventing additional proposal prerequisites in delegation summaries.
The adapter now preserves the original user message for specialists and clarifies
sales-only proposal routing. Sixteen focused local journey tests pass, including
a regression for model-generated prerequisite substitution. A new build,
`bld_01M661T2Y0RQA2MBKS55F6XJFD`, is in progress; its live acceptance is pending.

One additional invocation returned `POOL_EXHAUSTED`. Completed synthetic sessions
were stopped through the native runtime-session endpoint to release reservations,
retaining Engine history. This is a measured platform capacity response, not a
successful review test or an application retry. No unrelated session was stopped.

## Native review envelope correction

The routing-fix deployment `deploy-353c3710` succeeded at 09:26:01.022Z. Retesting
the same proposal produced the exact `fiber-500`/USD 89.90 native review. A changed
suspension generation returned HTTP 409 `RESUME_STALE_REVIEW`; the correct
generation returned HTTP 200/resuming. Resumption then failed before simulation:
the native endpoint records a JSON `human_review` envelope, whereas the adapter
expected the legacy per-interrupt decision dictionary.

The translator now strictly accepts the Engine-recorded native envelope and maps
`approved`/`rejected` to the domain decision. It preserves the legacy dictionary
contract, rejects unknown fields/values, and never reads a decision from caller
resume data. Journey workflow version 2 separates this change. Linux/amd64 passes
81 hosted-contract tests; the real AER replay test covers both native decisions.
Build `bld_01M6629HJ7T0QTMY1MG9CF1W8E` is in progress; successful live approval is
still pending. No plan simulation was released by the failed execution.

The application VoiceService completed a real synthetic TTS→STT probe:
`Read invoice demo-1.` became `Read Invoice Demo 1.` from 2.6 seconds of PCM. No raw
audio was persisted. This is provider-stage evidence, not microphone/listening or
complete browser-journey acceptance.

## Final hosted core acceptance and browser playback repair

Build `bld_01M6629HJ7T0QTMY1MG9CF1W8E` deployed successfully as
`deploy-926b87c0` at 09:33:15.802Z. The real Engine matrix passed approval after
native sandbox stop/restart, rejection, and approval after the five-minute deadline
returning `expired`. Changed action digest, another synthetic principal and stale
native generation were denied. The identity facade in that scripted matrix is a
labeled double; Engine executions, decisions, replay and tools are live.

Engine audit shows three model calls for both review flows, with no model
redispatch on resume. Approval alone executed `telco_simulate_plan_change`, exactly
once; rejection and expiry executed none. Two overlapping requests in one session
produced one completed execution and one conflict. The earlier mixed trace had
seven model calls, three tools, matching scope and 4,854 tokens. Synthetic sessions
were released after their controls, without deleting Engine history.

The Atlas-backed app started on http://127.0.0.1:53183. The user logged in and
obtained a completed financial/technical response, but reported inaudible playback.
A real Chromium regression with a valid synthetic WAV reproduced failure under the
original CSP and passed after adding only `media-src 'self' blob:`. The backend was
restarted with that policy; root HTTP tests still pass (42). Human listening retest
is pending; the earlier failure is not reported as voice acceptance.

Current Linux hosted contracts: 81 passed. Browser suite now includes the WAV
playback regression. Final source/build IDs, exact controls and synthetic payloads
are in [portable evidence](../../compatibility/phase2-journey-evidence.json).

## Phase 2 checkpoint

The user confirmed that audio worked after the CSP correction on 2026-10-30.
The final authenticated browser view showed a completed financial/technical
request with the exact invoice and network guidance. Seven Chromium tests pass,
including actual playback of a synthetic WAV under the deployed CSP. The source
retains strict script/frame/object controls; only media permits local Blob URLs.

Phase 2 is complete for the scoped demo: simulated business tools and receipts,
Engine-owned execution/memory/review, SDK orchestration, authenticated chat and
quiet-room browser voice. General transcript restoration, persistent CRM account
mutations, production capacity guarantees and governed retrieval are not claimed.
Phase 3 has not started. Publish this checkpoint manually on
`codex/phase-2-journey`; new remote CI remains pending until publication.
