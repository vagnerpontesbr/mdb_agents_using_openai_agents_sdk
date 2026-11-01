# I18N-001: Portuguese, English and Spanish across UI, responses and voice

- Status: LANG-0, LANG-2a and LANG-2b merged; LANG-2c source contracts locally validated, approved Atlas validators applied and three multilingual sources published/verified; LANG-2 hosted/HTTP acceptance passed; PR integration and LANG-3 pending
- Date: 2026-11-01
- Owner: Telecom demo maintainer
- Dependencies: UI-001 profile preferences, existing journey/voice contracts
- Decision: [ADR-0032](../adr/0032-multilingual-profile.md)

## Confirmed outcome

Support Portuguese (Brazil), English and Spanish for the interface, agent responses,
speech recognition and spoken output. Use `pt-BR`, `en-US` and `es-ES` locale keys,
matching the reference application's choices. Persist the user's choice in the
profile. User-visible localization supersedes the previous English-only requirement;
source identifiers, developer documentation and internal engineering instructions
remain English. Localized catalogs, templates, fixtures and user-facing agent
instructions necessarily contain the supported languages.

The confirmed profile scope includes display name, timezone, language, photo and
self-service password change. UI-001 owns profile security and storage; this task
owns cross-channel language semantics. No extra application role is introduced.

## Locale contract and invariants

- Existing profiles default to English until a preference is explicitly selected;
  avoid a bulk rewrite or silently inferring account preference from IP/location.
  The unauthenticated login page offers the same three choices; the authenticated
  persisted preference wins after login. Do not store credentials in browser storage.
- Validate the locale against the exact server allowlist. Resolve a locale snapshot
  at the start of each turn and propagate it through the API, hosted SDK orchestration,
  specialist tools, protected templates and voice stages. Locale is presentation
  context, never authorization or part of the user's identity.
- The requester explicitly requires the conversation to remain active during language changes. Preserve visible messages, draft input, session/execution IDs, pending approvals and in-flight transport/audio; do not unmount/restart the journey or duplicate requests. Existing messages retain their original language.
- Switching preference updates the interface immediately and applies to subsequent
  turns. It must not restart an execution, reapprove an action or reinterpret an
  in-flight proposal. The text and TTS for an execution use the same captured locale.
  Explicitly show any in-flight response in its original language after a switch.
- Use canonical UTC timestamps, integer money and unchanged currency codes for
  business logic. Localized dates/numbers are display only; Portuguese does not
  imply conversion from USD to BRL. Normalize locale-specific input before validation.
- Keep one Engine memory owner and stable user/session mapping across language
  changes. A changed preference must not create a second memory store or expose
  another user's remembered facts. Do not rewrite previous memory or transcripts.

## Interface and response design

Provide complete catalogs for navigation, profile, administration, Tokenomics,
knowledge, login, validation, loading/empty/error states, accessibility labels and
voice controls. Use stable message/error codes plus safe parameters, not string
matching on English exceptions. Test key/placeholder parity and meaningful fallback;
never expose raw backend/provider exceptions to obtain a translated error.

Introduce versioned deterministic templates for financial facts, plan proposals,
approval/rejection, recovery and unavailable-service responses in all three locales.
Cover both `src/telecom_app/rendering.py` and the actual hosted adapter/domain path;
changing only the unused/local renderer is not sufficient. Exact text tests apply
to each critical template. Localized explanations use semantic evaluation, not
arbitrary exact assertions against LLM prose.

RAG citations preserve original source identity/version/pages and source language.
Do not translate operational instructions through an unchecked final LLM rewrite.
Prepare governed localized synthetic procedures or reviewed translations with
source lineage in each locale for the acceptance dataset. If the approved localized
procedure is unavailable, provide a localized safe explanation and clearly identify
the source language; do not invent translated operational steps. Map this design
against existing language/applicability filters before modifying retrieval contracts.

## Voice design

Current `VoiceService.transcribe` supplies `language="en"`; replace that fixed hint
with validated locale mapping (`en`, `pt`, `es`) after checking the pinned SDK/provider
contract. Send the final verified localized answer to TTS. Keep current models and
provider routing unless evidence justifies a separately reviewed change.

Test microphone permission, silence, malformed PCM, interruption and uncertain
outcome in all locales. Keep recording limits and raw-audio retention disabled.
Numbers, prices, dates, names and negations need explicit multilingual recognition
and listening examples. Mock WAV tests establish transport, not pronunciation.

Official [TTS supported languages](https://developers.openai.com/api/docs/guides/text-to-speech#supported-languages)
includes English, Portuguese and Spanish and notes English-optimized voices. This
documentation is not evidence that this app's complete multilingual voice path has
passed. Verify transcription support and actual pinned SDK behavior in LANG-0.

## Phases and tests after each change

| Phase | Deliverable | Quality gate |
| --- | --- | --- |
| LANG-0 — Contract and inventory | Locale precedence/snapshot, text inventory, error codes, template and source-language strategy, pinned voice API check | Every surface mapped; no authorization or identity dependence on locale; meaningful three-language synthetic dataset and listening script prepared |
| LANG-1 — UI i18n | Three catalogs, profile language selection, login selector, number/date formatting, all Control Plane/Tokenomics states | Switch languages during text streaming, pending approval and audio playback: conversation, draft and execution remain active, no duplicate action/request, next turn uses the new locale; no missing keys/placeholders; persisted preference isolated per user; reload/logout behavior; keyboard/ARIA, 390/1440px and long translated labels; no raw error leakage |
| LANG-2 — Agent responses | Locale propagation through actual hosted execution, deterministic templates, safe localized knowledge behavior | Exact protected templates for all locales; same amounts/action digests/permissions; language-specific prompt injection and other-user denial; cross-language memory continuity; unsupported locale rejected |
| LANG-3 — Voice and integration | STT hints, localized TTS, text/audio consistency, full three-language walkthrough | Transport and regression suites pass; bounded real transcription/TTS examples in each language; human listening acceptance for clarity and critical numbers. Record unperformed listening as pending, never infer it from a WAV or transcript |

LANG-0 starts with UI-0; LANG-1 integrates with UI-1/UI-2a. Tokenomics must consume
the common catalogs from its first implementation. LANG-2 precedes LANG-3; both are
required for expanded UI-4 final acceptance. Hosted changes require hosted contract
tests and a controlled deployment/version compatibility gate; navigation alone does
not authorize a deployment. No simultaneous Engine memory cutover and locale rollout.

Use existing frozen frontend/backend checks, plus hosted contracts where changed.
Run deterministic tests per phase and record bounded live checks separately. A live
rehearsal needs a declared call/time cap within remaining authorization; pause for a
decision if that cannot be established. No pricing or production-capacity proof is
required. Commits, pushes, PRs and automatic merges are authorized per phase after
quality/CI gates pass; pause and ask if a material design question remains.

## Evidence

Planning inspected the current hardcoded STT hint, English templates and profile
contracts, and fetched official TTS language documentation. No translation catalog,
profile persistence, password/photo endpoint, provider call or deployment has been
implemented or validated by this planning update.


UI-2a progress: interface catalogs, profile/login language selection and timestamp/
number presentation are implemented locally; tests cover catalog parity, persistence,
active-request continuity and audio-object continuity. See UI-001 for exact results
and the passed Atlas profile write gate. LANG-0 provider/template/source inventory and
LANG-2/3 hosted response/speech gates remain incomplete. Historical provider prose
and governed source metadata are deliberately not translated by the UI catalog.


## LANG-0 inventory — 2026-11-01

[Multilingual rollout](../runbooks/MULTILINGUAL.md) maps current source owners,
locale transport/replay compatibility, English-only knowledge constraints, pinned
speech API behavior, semantic test inputs and the human listening script. No runtime
behavior or provider configuration is changed by this inventory. Retain the selected
voice models for this iteration; their documented shutdown dates require a separate
migration before January/February 2027. LANG-2 must prove durable locale transport
and governed source handling before a hosted rollout.


## LANG-2 subphases and acceptance

LANG-0 merged in PR #10 as `8810449`. Source commit `4658e5f` passed repository and
application CI in runs `41340434042` and `41340450806`; neither run failed.

- LANG-2a: bounded hosted presentation proof. Add versioned templates, strict turn
  envelope parsing, typed response locale and real SDK tests with Engine doubles.
  Preserve legacy English calls and exact action arguments. This is not activation
  of profile-to-hosted propagation or completion of LANG-2.
- LANG-2b: application admission/recovery/UI propagation, local invoice template,
  consistent error codes, and staged compatibility with deployed Engine contracts.
  The new carrier must not be enabled against the old hosted deployment.
- LANG-2c: governed localized sources and full bounded hosted semantic/memory
  acceptance. Prepare exact source/validator/deployment changes and inspect shared
  consumers before requesting any needed Atlas approval. Only then close LANG-2.

### LANG-2a implemented behavior

The hosted adapter accepts legacy plain text as en-US or a strict
`telecom-turn-v2` message envelope containing only locale and message. It rejects
unknown locales, extra identity fields, duplicate JSON keys and oversized input,
and does not recursively interpret the user message. Memory retrieval receives the
original user text and unchanged user/session context. This is an application
message format using the existing Engine message field, not a new native metadata
API. The HTTP application does not emit it yet.

The SDK injects validated presentation locale into read-tool calls; English defaults
preserve existing arguments. Financial/connection/plan outputs use deterministic
three-language templates. Original requester, plan ID, minor units, currency and
proposal digest are unchanged. Native simulation arguments are unchanged; a checked
receipt is localized only after scope/price/reference validation. Rejection, expiry
and clarification are deterministic. Result.locale defaults to en-US for old records.

A non-English approved-procedure request returns a localized explanation that the
current source language is English. It neither searches with weaker applicability
filters nor translates operational steps. This temporary safe path does not count
as localized knowledge availability; LANG-2c still requires governed sources.
Ingestion status localization also remains for that phase.

### Local gates and failures

- All **95 hosted contract tests** passed using SDK 0.24.0 and Engine SDK/runner
  0.11.11 with doubled transport. Added coverage includes exact invoices, locale
  validation, unchanged proposals, request-scoped memory identity, cross-user denial,
  missing-procedure fallback, and native review/receipt presentation.
- Ruff F checks passed on the six changed Python modules; adapter wheel and source
  distribution built successfully. No frontend or application runtime changed.
- Initial tests could not start because sandbox cache access was denied, then because
  the adapter environment was absent and uv could not discover Python 3.15.2. A
  frozen sync using the already verified `/tmp/telecom-python-manual/python/bin/python3.15`
  created the environment without changing pins.
- `test_wrong_subject_is_denied_in_each_language` initially expected a direct
  UnsupportedContract. The SDK correctly denied the result but wrapped that exception
  in UserError. The test now checks the wrapper and original cause; all languages pass.
  Ruff found one unused json import in journey.py; removed and rerun passed.
- No provider calls, live memory continuity proof, Atlas mutation, hosted deployment
  or end-user listening was performed. Full LANG-2 and LANG-3 gates remain open.


### LANG-2b application admission and recovery

LANG-2a merged through PR #11 as `1ca1a66`. Its source commit `2d18f10` passed
repository/application CI runs `41341351639` and `41341367933`; neither failed.

New text requests snapshot the authenticated profile locale before streaming starts.
The application emits the strict carrier only when APP_JOURNEY_LOCALE_ENABLED=true;
its default is false and no live environment file is changed. This compatibility
switch is private deployment configuration, not an editable Control Plane toggle.
New localized invocations require the Engine to return the exact original message.
Missing/mismatched native input fails without retry or a success claim.

Native execution.message supplies the locale on recovery, suspension and errors.
Completed result.locale must match that input. Legacy records default to en-US;
unknown locales fail closed. Changing profile preference or restarting the backend
cannot change a saved execution's language or approval digest. No local execution
or memory store is introduced. The pinned runner's Execution model contains message;
the official [execution detail schema](https://www.mongodb.com/docs/agentengine/sdk/javascript/packages/agent-engine-runner-shared/docs/api/)
also exposes it. Live carrier/maximum-length acceptance is still pending.

The interface labels response language and sets its lang attribute; historical prose
is preserved. Proposal amount formatting uses captured locale. Chat progress/error
SSE now includes stable codes; progress renders a known catalog key. The independent
local invoice renderer has exact pt-BR/es-ES templates but is not presented as a
substitute for hosted-path acceptance.

Validation: 189 foundation tests passed before the final input-roundtrip assertion;
the affected journey/locale suites were rerun afterward (39 tests). Hosted contracts
passed 96 tests, including actual application-producer/adapter-consumer wire agreement.
Ruff passed after fixing two E501 line-length findings; mypy passed for 30 files.
Frontend lint, six unit tests and typecheck/build passed. All 19 browser tests passed;
a focused language-switch rerun passed after visual review corrected untranslated
history role labels and replaced the locale code with a readable language name.
The 390px capture has no horizontal clipping. These are local fixtures, not provider
language or listening evidence. No behavior assertion failed in this subphase.

Next gate: prepare the hosted rollout and governed localized knowledge acceptance.
Keep the compatibility switch false until the exact deployed agent, read-tool schemas,
original-message recovery and provider behavior pass the controlled rehearsal. Do not
roll out while old active/suspended executions lack a verified replay path. LANG-3,
admin configuration, actual costs and memory migration remain subsequent work.


### LANG-2c source-contract gate

LANG-2b merged in PR #12 as `e0c9d4f`. Source commit `da82565` passed repository and
application jobs in runs `41342524087` and `41342543625`; no remote check failed.
The Engine CLI initially returned HTTP 401 during read-only workspace inventory.
The existing refresh-token flow succeeded without exposing credentials; subsequent
reads found agentsdk and geo-intelligence-network in the same project. No workspace,
policy, deployment or memory setting was mutated.

[ADR-0033](../adr/0033-governed-language-source-lineage.md) records additive language
and original-source lineage rules. Local upload metadata can represent en/pt/es and
an optional translation_of original-version key. The old English approval hash and
serialized review metadata remain unchanged when that field is absent. Parent
eligibility is rechecked before source release, including cached translations.

Read-only Atlas inspection compared both current validators to the baseline and
counted documents incompatible with the proposed validators: zero. The exact
[proposal](../../compatibility/lang2c-validator-proposal.json) changes only validators
on telecom_demo_knowledge.document_versions and telecom_demo_knowledge.chunks.
The requester approved exactly these two validators. Both were applied and verified
by readback in strict/error mode; zero existing documents were incompatible. See
[applied evidence](../../compatibility/lang2c-validator-evidence.json). No documents,
roles, indexes, policies, deployments or memory were written. The executed command was:

```sh
uv run --env-file .env --frozen python scripts/apply_language_validators.py \
  --proposal compatibility/lang2c-validator-proposal.json --apply-approved-change
```

Local validation: the final full suite passed **209 foundation tests** and **96 hosted
contracts**. All 19 language/migration cases passed, including preflight-before-write,
proposal tampering, partial application and absence of an explicit apply flag.
Ruff initially found an import-order issue and four overlong lines; these were
corrected. The repository check also initially rejected three missing required ADR
sections; alternatives, consequences and revisit triggers were added. No behavioral
test failed. These tests use database doubles; the Atlas
readback verifies the configured validators but does not establish actual invalid-insert rejection.

Localized retrieval now captures the authenticated profile locale, applies the same
language to lexical/vector filters, and preserves tenant/ACL/equipment restrictions.
The hosted tool receives the captured turn locale. Extracted source text is unchanged;
citation labels and safe refusals are localized. Missing matches do not claim an
English original exists. The source library preserves access to eligible historical
citations across locale changes. Upload and native-review UI expose source language
and original-version linkage; translations are excluded as parent choices.

Actual reviewed multilingual sources and bounded provider/hosted acceptance remain
pending inside LANG-2c. Keep new locale admission disabled until its live gate passes.
The validator authorization does not authorize arbitrary source publication or other
Atlas changes. No translated source has been published and no hosted rollout occurred.

Continuation validation (2026-11-01; local working tree, not remote CI):

| Command | Result and scope |
| --- | --- |
| `uv run --frozen pytest -q` | 213 passed; source authority, language filters, cache and application regression |
| `uv run --frozen pytest -q tests/foundation/test_knowledge_languages.py` | 17 passed after removing an unsupported English-source assertion from the safe refusal |
| `uv run --project compatibility/openai_engine_adapter --frozen python -m unittest discover -s tests/hosted_contract -q` | 96 passed; native tool contracts and captured locale dispatch, with doubles |
| `uv run --frozen ruff check src/telecom_app tests/foundation` | Passed |
| `uv run --frozen mypy` | Passed, 30 source files |
| `npm --prefix apps/web run lint` | Passed |
| `npm --prefix apps/web test` | 6 passed |
| `npm --prefix apps/web run build` | TypeScript and production build passed |
| `TELECOM_TEST_PORT=53189 npm --prefix apps/web run test:e2e` | 20 passed, isolated server; upload locale/parent payload, native review and existing continuity regressions |
| `python3 scripts/check_repository.py` | Passed, 92 Markdown files and 33 ADRs in the final check |
| `git diff --check` | Passed |

Failures and corrections: the initial TypeScript build rejected rendering unknown
translation metadata (TS2322); a string type guard corrected it and the build passed.
Ruff reported six E501 lines in retrieval/tests; wrapping fixed them and Ruff passed.
The first browser run passed 19 tests but the new translation-upload case timed out
on an exact `getByLabel` lookup for the nested select. The control was present with
the correct accessible name; `getByRole('combobox', {name: 'Source language', exact:
true})` selects it correctly. The complete rerun passed all 20, including the exact
Portuguese language/original-key payload assertion. No live provider, invalid-insert,
translation-fidelity or human listening acceptance is implied by these results.

### LANG-2c synthetic source packet

Prepared [three one-page PDFs and a bounded publication proposal](../../examples/telecom/governance/multilingual/README.md).
The original is English; Portuguese/Spanish declare exact original-version lineage.
Local Docling 2.143.1 extraction passed for all three with identical checksums and
all four operational steps/negations preserved. Poppler visual inspection passed
for all three. [Evidence](../../compatibility/lang2c-source-evidence.json) explicitly
records zero provider calls, zero Atlas writes and no native approval in this step.
ReportLab 4.4.3 lives in an isolated script lock, not the application dependencies.
The first verification invocation encountered a sandbox uv-cache permission error;
the authorized escalation rerun passed without altering the validation.

The knowledge-review source profile was staged locally (26 source files), without
a Linux interpreter bundle, upload or deployment. A deployable runtime build and
in-flight replay gate are still required. PR #13 is draft; remote repository and
application checks passed for 834e28e in runs 41343579558/41343610424. These checks
do not validate the later uncommitted source/UI/packet changes.

The requester subsequently approved this exact three-source publication and provider
envelope with "sim aprovo". The ceiling was not increased. See the executed gate
below; hosted deployment remains outside that authorization.


### LANG-2c live publication and direct retrieval gate — passed

[Live evidence](../../compatibility/lang2c-publication-evidence.json) records three
native owner approvals and published SOP-LANG-OPTICAL-EN/PT/ES, version 20261101-1.
The translations reference the exact published English original. The frozen proposal
retains its original draft status so its approved SHA-256 remains stable; evidence
records authorization and actual state separately.

Executed `uv run --env-file .env --frozen python scripts/publish_multilingual_sources.py`
for read-only preflight, then the same command with `--apply-approved-change
--allow-provider-calls`. It verified unused IDs, source bytes, current dates, owner,
cluster, exact strict/error validators and deployment deploy-af009ed4 before writes.
The native review's complete metadata was compared with the uploaded version before
each approval; publication and original-byte retrieval then passed. No existing
source was replaced, no schema/policy/role/index changed and no deployment occurred.

Exactly nine Voyage/gateway calls ran: three document embeddings, three query
embeddings and three reranks; no automatic provider retry. Total elapsed time was
124.81 seconds, below the approved 20 minutes. All three direct retrievals returned
their source citation and complete operational steps/negations within the hosted
response bound. Wrong-tenant and wrong-ACL searches returned no candidates for each
language, reusing vectors without additional provider calls.

The initial preflight failed with EngineUnavailable before any writes or provider
calls. Refreshing the existing private CLI session succeeded; repeated preflight
passed. Ruff initially found import ordering in the new operator script; corrected
and rerun successfully. A read-only metadata helper hit the uv cache sandbox boundary;
the approved escalation succeeded. No provider or publication execution failed.

Additional local checks: 23 tests passed across test_knowledge_languages.py,
test_curation.py and test_document_review.py; script Ruff F/I and repository/diff
checks passed. These targeted reruns do not represent a new complete CI run.

Remaining LANG-2c gate: controlled hosted locale rollout, original-message/replay
acceptance, cross-language memory continuity and bounded semantic chat evaluation.
APP_JOURNEY_LOCALE_ENABLED remains disabled. Operator-admitted publication is not
browser authentication acceptance. Voice/listening remains LANG-3. Billing is still
unreconciled; the successful bounded exercise is not proof of a measured dollar cost.


### LANG-2c hosted rollout preparation

The [exact rollout proposal](../runbooks/LANG_2_HOSTED_ROLLOUT.md) and
[Linux build evidence](../../compatibility/lang2c-hosted-build-evidence.json) are ready.
Local knowledge-review registration now uses workflow 9, separating changed locale
semantics from the deployed workflow 8. The staged manifest matches the recorded
Phase 7 manifest byte-for-byte; no tool, secret or egress scope was added.

Executed the compact Python staging command, pinned Docker Linux/amd64 build with
uv frozen dependencies, and all 96 hosted contracts inside that container. All passed.
A separate container loader check returned Python 3.15.2/x86_64, KnowledgeExecution,
telecom-journey version 9 and seven tools. The 213-test foundation suite also passed.
The first exploratory `agentengine execution --help` returned unknown command;
o execution was changed. Official execution-list/cancel API documentation supplied
the supported interface. Read-only uv helpers initially hit the sandbox cache
restriction and succeeded after approved escalation; no behavioral test failed.

[Inventory](../../compatibility/lang2c-rollout-inventory.json) found one legacy
suspended release_synthetic_recall execution from October 29. The three runtime
reservations match completed publication tests; no other reserved sessions were
found. Neither cancellation nor runtime release has been performed. Runtime-session
counts alone would have missed the suspended execution, so rollout must recheck
both native execution statuses and runtime reservations.

Pending requester decision: cancel the exact legacy suspended execution; release
only the three completed test runtimes; build/deploy the reviewed stage in agentsdk
and run the proposed 20-invocation/30-minute acceptance envelope without increasing
the USD30 ceiling. No memory configuration or geo-intelligence-network change is
proposed. All files remain local; remote CI for the later working tree is pending.


### LANG-2c hosted and HTTP acceptance — passed

The requester approved the exact rollout with "sim autorizo". Build
bld_01M6CCNAB7QA912HBH54FB63ZP and deployment deploy-f11e4d01 succeeded.
[Remote rollout](../../compatibility/lang2c-remote-rollout.json) and
[hosted acceptance](../../compatibility/lang2c-hosted-acceptance.json) record all
20 planned cases passing in 486.41 seconds, with no invocation retries.

Coverage: exact invoice templates in all locales (including the 4,000-character
message carrier); governed PDF excerpts/citations; information-only negation;
authorization injection; same-user English-to-Portuguese/Spanish memory continuity
and other-user isolation; three native simulations (one rejection, two approvals);
Portuguese runtime-stop/recreation with identical pending action; stale, cross-user
and duplicate approval denial; and legacy unwrapped English input. Every completed
result was recovered after a profile-language switch with its original locale.
Both synthetic profiles were restored. These are bounded synthetic cases, not
statistical multilingual-quality or cross-version-replay guarantees.

[HTTP evidence](../../compatibility/lang2c-http-recovery-evidence.json) additionally
records an isolated loopback server backed by the real identity and Engine services:
20 stored results matched their hashes/locales and all 20 cross-user reads returned
403. It added zero provider calls. The server was stopped; existing demo processes
were not restarted. Native active-status counts were zero after the evaluator and
the other workspace's active deployment remained deploy-e5f6797e.

The private local .env now enables APP_JOURNEY_LOCALE_ENABLED for the next backend
start. The checked-in default remains false so a different deployment cannot admit
new locale envelopes before its own gate. Text localization is validated; STT hints
and human voice listening remain LANG-3. No password change or memory configuration
change occurred. Provider monetary billing is still unavailable; the USD30 ceiling
was not reset or increased.

Failures: the first evaluation preflight used stale workspace deployment metadata,
failed before any invocation and is preserved separately. Official
`deployments/current` verified the exact new active build and complete health;
correcting the preflight to use that endpoint allowed the full evaluation.
`agentengine status` continued showing the old summary; this is a diagnostic
limitation, not evidence that the old build handled the successful localized calls.
No live behavioral case failed. See the rollout runbook for the earlier CLI/import
and sandbox errors and their successful corrections.

Repository/diff checks and script Ruff passed. The earlier local 213 foundation,
96 Linux hosted, 6 frontend unit and 20 browser checks remain recorded above;
remote CI must validate the final published commit before merging PR #13.

The first staged diff check treated the ASCII-compatible PDF containers as text
and flagged required PDF cross-reference whitespace. Added `*.pdf binary` in
.gitattributes to preserve exact governed bytes and prevent text/EOL transformations;
no approved PDF bytes or hashes were changed. The staged diff check then passed.
