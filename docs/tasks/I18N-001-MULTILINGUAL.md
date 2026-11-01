# I18N-001: Portuguese, English and Spanish across UI, responses and voice

- Status: LANG-0 and LANG-2a merged; LANG-2b application propagation locally validated, remote gate pending; full LANG acceptance pending
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
