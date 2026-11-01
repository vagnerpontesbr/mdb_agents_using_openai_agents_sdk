# LANG-3: Captured voice language

## Scope and state

LANG-3 is accepted for the bounded three-language demo after the requester explicitly
answered "sim aceito". English corrected TTS/STT and browser voice in all three
locales passed the recorded requester checks. The complete nine-case matrix is a
known limitation, explicitly excluded from this acceptance. Publication/CI is pending.
The chronological records below preserve original failures and subsequent evidence.
No Engine deployment or shared Atlas configuration was changed.

## Implemented contract

- Recording captures the selected interface/profile locale before microphone permission.
  Changing preference while recording or transcribing does not reinterpret that audio.
- `/api/voice/transcribe` accepts an allowlisted locale (legacy default en-US), sends
  en/pt/es to the pinned SDK and returns text plus the captured locale. No raw audio
  is persisted. The transcript remains editable and requires explicit Send.
- A transcript draft retains its locale through edits and preference changes. Emptying
  the draft clears its audio origin. Subsequent typed turns use the server profile.
  The UI displays the captured audio language and AI-generated speech disclosure.
- Chat accepts optional `audio_locale` as presentation context only. The existing
  authenticated user/session and Engine authorization still own admission. This
  field is not proof that text came from a microphone and grants no permissions.
  Text-only requests keep server profile precedence. Non-English voice admission
  is rejected while APP_JOURNEY_LOCALE_ENABLED is false.
- TTS reads only an authorized completed Engine result, using its durable locale
  rather than the current profile. The verified text is unchanged. Locale-specific
  pronunciation instructions and Content-Language identify the original response.
  Instructions are not proof of pronunciation or semantic accuracy.
- Stop playback invalidates a pending audio download as well as pausing current
  audio. Leaving Support discards capture and prevents late audio playback; changing
  locale alone does neither. Failed transcription preserves the previous draft and
  does not submit chat or retry automatically.

Pinned models remain gpt-4o-mini-transcribe / gpt-4o-mini-tts, alloy, SDK 0.24.0,
OpenAI 3.40.0. PCM limits remain mono 24kHz, 16-bit, 15 seconds input / 120 seconds
output, no retries and disabled transcription trace audio. Official contracts and
announced model retirement dates are recorded in [MULTILINGUAL](MULTILINGUAL.md).
No Engine adapter or workflow change is needed for this application boundary.

## Authorized live gate — semantic failure, continuation stopped

1. Run the six-request synthetic speech evaluator (3 TTS + 3 STT, at most 10 minutes):

   ```sh
   uv run --env-file .env --frozen python scripts/check_multilingual_voice.py --allow-provider-calls
   ```

   Without the explicit flag it prints a dry-run plan and sends no requests. It
   reserves `artifacts/lang3-voice` before calling; an existing directory prevents
   accidental rerun. Synthetic WAVs and sanitized evidence stay in ignored artifacts.
   It aborts on the first failure or oversized audio, without truncation/retries.
   Inspect exact numbers, dates, name, plan and negation in each transcript. A
   successful round trip remains transport evidence, not human listening acceptance.
2. With the requester present, use the invoice, negated-offer and simulation rows
   from [the listening script](MULTILINGUAL.md#synthetic-acceptance-dataset-and-listening-script)
   in each of three locales: at most 9 hosted invocations and 18 speech requests.
   Use existing synthetic users and fixtures; do not approve any proposed action.
   Check transcript before Send and record intelligibility and critical facts for
   all nine replies. Raw microphone recordings must not be saved. Verify live
   locale switching and same-conversation continuity.
3. Total proposed envelope: **24 speech requests + 9 hosted invocations**, 30 minutes
   combined, zero retries. Hosted invocations can contain multiple provider calls;
   these are not described as 33 raw model requests. Stop at either bound or any
   observed budget exhaustion. This does not increase or reset the existing USD30
   ceiling; billing remains unreconciled. No Atlas configuration or memory change.

A live gate also needs an isolated updated backend/frontend; preserve existing demo
servers. Record the actual command, run identity, versions, durations and pass/fail
observations. Do not infer approval or listening from elapsed time. Publication and
CI must be recorded separately from local tests.

## Local verification

See [I18N-001](../tasks/I18N-001-MULTILINGUAL.md) for commands, counts and failures.


## Live result — 2026-11-01

Executed the authorized evaluator command above: six requests (three TTS / three
STT), 11.85 seconds, zero retries and zero hosted invocations. All three WAVs and
transcripts returned, but transport success did not satisfy semantic acceptance.
[Reviewed evidence](../../compatibility/lang3-voice-evidence.json) preserves actual
transcripts and WAV hashes; the original transport report remains in ignored artifacts.

- English: input USD 79.90 became USD 7,990 in the transcript. This fails the critical
  amount gate. Name/date/negation were preserved. TTS versus STT fault origin is
  unresolved until the requester listens to the existing WAV.
- Portuguese: amount/date/negation were preserved, but Marta became Martha. Name
  spelling needs review; pronunciation alone cannot guarantee orthographic identity.
- Spanish: the transcript preserved name/amount/date/negation. The plan identifier
  had spacing/case differences, as in the other languages. Human listening is pending.

Stopped before the nine hosted walkthroughs. No automatic rerun, model change,
verified-text rewrite or inferred listening approval. The original 30-minute wall
clock envelope started at approximately 21:54 UTC; unused calls do not authorize
continuation after that time window. Diagnose with existing audio before proposing
any corrected bounded retest. LANG-3 remains incomplete and uncommitted.


### Requester listening feedback and candidate correction

The requester listened to en-US.wav and reported Spanish speech. English listening
acceptance therefore failed independently of the amount transcription. All three
on-disk WAV hashes match the original evidence. Three new tests exercise the real
Agents SDK and OpenAI client through HTTP serialization using MockTransport: the
English input and American English instruction are present in the request body.
This rules out omission at that tested client boundary, not a provider/routing issue
or a presentation issue in the user's playback application.

Candidate correction strengthens TTS instructions to keep one language throughout
and read monetary decimals as currency units/cents instead of thousands. Verified
input text, model, voice and provider path stay unchanged. This is not a proven fix.
Proposed diagnostic retest: exactly one English TTS request, no STT or Engine calls,
at most two minutes, separate output/evidence preserving the original failure.
Request new explicit approval because the prior failed batch prohibited retries.
The USD30 ceiling is unchanged; human listening must verify language and amount.


### Authorized single English TTS retest

The requester approved the bounded retest with "sim". Executed
`uv run --env-file .env --frozen python /tmp/telecom_lang3_english_retest.py`.
Exactly one TTS request returned in 2.71 seconds; zero STT requests,
zero hosted invocations and no retry. Local WAV inspection verified mono 24kHz
16-bit audio (8.95 seconds) and the recorded SHA-256.
[Retest evidence](../../compatibility/lang3-english-retest-evidence.json) records transport only: requester listening for English
and USD 79.90 remains pending. The original failed audio/evidence was preserved.
No commit, deployment or successful semantic correction is claimed.


The requester subsequently answered "sim" to the explicit checks for English speech
and 79 dollars / 90 cents. The single English TTS retest therefore passed human
listening for language and amount. This does not supersede the original failed
round-trip evidence or establish corrected STT, Portuguese/Spanish listening, or
the nine-case microphone walkthrough. No additional provider request was made.


The requester confirmed "sim os dois audios estao corretos" for the existing
Portuguese and Spanish samples, explicitly asked about language, clarity and
USD 79.90. Both original samples passed human listening for those criteria.
Together with the separate corrected English sample, all three languages now have
listening evidence. Portuguese/Spanish were generated before the revised TTS
instruction; this is not acceptance of the revised instruction across all locales.
The original English STT amount failure and Portuguese name spelling difference
remain recorded. Corrected English STT and the browser microphone walkthrough
remain unperformed. No provider calls or deployments occurred in this update.


### Renewed microphone acceptance window

Requester approved 19 speech requests and 9 hosted invocations within 30 minutes.
One STT request transcribed the corrected English WAV in 2.61 seconds:
Marta, fiber 500, USD 79.90, December 1st 2026 and the negation were preserved.
[Evidence](../../compatibility/lang3-stt-retest-evidence.json) records semantic review.
The initial read-only Engine preflight failed with EngineUnavailable; the existing
private CLI refresh succeeded, and a second read verified deploy-f11e4d01 healthy.
No deployment was performed and no credentials were printed.

Started a temporary loopback application at http://127.0.0.1:53191; startup and
GET / returned HTTP 200. Existing servers were preserved. Its temporary wrapper
limits further speech admissions to 18 and chat admissions to 9, until 19:42:47
America/Sao_Paulo on 2026-11-01; counters conservatively count even rejected requests.
Approval decisions are blocked; rejection remains available for test simulations.
No raw microphone audio or transcript is logged by the wrapper. Admission counts
live in ignored artifacts/lang3-browser-window/http-admissions.json. The wrapper
is an operator test harness, not a shipped application rate-limit implementation.
Browser microphone/listening acceptance remains pending requester participation.


### Requester browser feedback — coverage reconciliation pending

The requester reported "os testes foram ok". The isolated server ledger recorded
4 transcription admissions, 4 chat admissions and 2 playback admissions, all HTTP
200. [Snapshot evidence](../../compatibility/lang3-browser-evidence.json) retains
only counts/routes/statuses. It cannot identify locale/case or establish a successful
SSE result from HTTP status alone. This is less than the proposed nine-case script,
so explicit mapping of the completed cases was requested before closing the gate.
Do not report nine passed browser voice cases or silently waive the remaining
coverage. The server remains open within its original deadline for clarification;
no additional provider calls were initiated by the agent in this update.


### Three-language browser confirmation

The requester clarified that the initial working tests were English and Portuguese,
then tested the Spanish invoice prompt and reported that it worked. The updated
ledger shows 5 transcription admissions, 5 chat admissions and 3 playback admissions,
all HTTP 200. Semantic success and the language mapping come from requester feedback,
not from HTTP status. Browser microphone/response functionality is now requester-
confirmed in all three locales.

The renewed window used one separate English STT request plus eight browser speech
admissions and five chat admissions, within the authorized 19/9 caps. No new calls
were initiated during this evidence update. The complete nine-case invoice/negation/
simulation matrix is not established by these observations and must not be reported
as nine passed cases. The original failure and subsequent corrections remain intact.
No new automated test rerun is needed for this documentation-only update; repository
and diff checks are run separately. Changes remain local, without LANG-3 remote CI.
