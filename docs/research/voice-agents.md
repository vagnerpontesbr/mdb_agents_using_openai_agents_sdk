# Voice agent assessment

Official source fetched on 2026-10-28: [Voice agents](https://developers.openai.com/api/docs/guides/voice-agents).

## Confirmed capabilities

The guide distinguishes GPT-Live with a separate reasoning backend, Realtime speech-to-speech sessions, and chained speech-to-text → agent → text-to-speech. It documents Python agents.voice.AudioInput, SingleAgentVoiceWorkflow, and VoicePipeline with streamed audio. The Realtime starting point uses RealtimeAgent and RealtimeSession; this does not establish identical Python/browser SDK APIs.

## Initial delivery recommendation

Connect browser voice to the same Python supervisor and specialists as chat through a chained pipeline. Keep authorization, tools, memory, retrieval, and approvals in one workflow. Use the SDK voice pipeline where its session interface fits; otherwise implement a documented custom workflow adapter after checking the pinned SDK. The minimal SingleAgentVoiceWorkflow example alone does not prove compatibility with external memory/session adapters.

- React: microphone permission, recording, playback, transcript, mute/cancel, device and connection recovery.
- Backend: normalize browser audio to the required codec/sample rate and test conversion.
- Carry authenticated identity and conversation IDs across channels. Deduplicate committed transcripts; partial recognition is not durable memory.
- Validate answers before speech synthesis where required. Spoken confirmations must match business outcomes.
- Cancellation stops pending audio/generation where supported; it does not roll back completed tools.
- Provider credentials stay server-side; authenticate the application audio transport.
- English is the default interface, conversation, and voice language.
- Raw audio retention is off by default; evaluation recordings require separate access/retention policy.

The baseline is controlled turn-based voice, not a claim of full duplex. GPT-Live/Realtime can be separately validated low-latency adapters. PSTN/SIP requires a provider and call identity/transfer contract; browser voice does not imply telephone-network integration.

## Acceptance

Complete a spoken technical request with a cited, audible answer, then switch to text in the same conversation. Test names/numbers, noise, recognition corrections, denied microphone access, disconnects, cancellation, and tool failures. Retried audio/events must not duplicate business effects. Measure useful audible latency and task correctness separately; include human listening.

Exact voice dependencies, session integration, codecs, speech models, and Engine audio/streaming transport remain implementation compatibility gates.
