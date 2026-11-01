# I18N-001: Portuguese, English and Spanish across UI, responses and voice

- Status: Interface/profile delivered through UI-2c; LANG-0 inventory prepared, remote gate pending; full LANG acceptance pending
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
