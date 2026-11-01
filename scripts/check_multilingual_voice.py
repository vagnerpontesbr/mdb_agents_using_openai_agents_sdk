#!/usr/bin/env python3
"""Six-call synthetic speech gate; dry-run by default, no microphone capture."""
import argparse
import asyncio
import base64
import hashlib
import io
import json
import os
import time
import wave
from pathlib import Path

from telecom_app.voice import VoiceService, pcm_bytes

CASES = {
    "en-US": "Marta, do not change fiber-500. The total is USD 79.90, due December 1, 2026.",
    "pt-BR": "Marta, não altere o fiber-500. O total é USD 79,90, vence em 1 de dezembro de 2026.",
    "es-ES": "Marta, no cambies fiber-500. El total es USD 79,90, vence el 1 de diciembre de 2026.",
}


async def evaluate(destination):
    # Reserve the evidence location before the first call: never rerun an uncertain batch.
    destination.mkdir(parents=True, exist_ok=False)
    report = {"status": "started", "provider_requests_started": 0, "cases": [],
              "human_listening": "pending", "microphone_walkthrough": "pending",
              "models": ["gpt-4o-mini-tts", "gpt-4o-mini-transcribe"],
              "call_cap": 6, "time_cap_seconds": 600}
    started = time.monotonic()

    def save():
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        (destination / "evidence.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    save()
    try:
        async with asyncio.timeout(600):
            service = VoiceService()
            for locale, text in CASES.items():
                report["provider_requests_started"] += 1
                save()
                audio = await service.speak(text, locale)
                (destination / f"{locale}.wav").write_bytes(audio)
                with wave.open(io.BytesIO(audio)) as wav:
                    assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 24000)
                    encoded = base64.b64encode(wav.readframes(wav.getnframes())).decode()
                pcm_bytes(encoded)  # Enforce the unchanged 15-second admission bound.
                report["provider_requests_started"] += 1
                save()
                transcript = await service.transcribe(encoded, locale)
                report["cases"].append({"locale": locale, "source_text": text,
                    "transcript": transcript, "wav_sha256": hashlib.sha256(audio).hexdigest(),
                    "semantic_review": "pending: check name, plan, amount, date and negation"})
                save()
        report["status"] = "transport_passed_review_pending"
    except Exception as error:
        # Provider exception details can contain request information; retain only its class.
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        raise SystemExit("Speech gate failed; inspect sanitized evidence. Do not retry automatically.") from None
    finally:
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-provider-calls", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("artifacts/lang3-voice"))
    args = parser.parse_args()
    if not args.allow_provider_calls:
        print(json.dumps({"mode": "dry_run", "calls": 6, "seconds": 600,
                          "cases": CASES, "human_listening": "required"}, ensure_ascii=False, indent=2))
        return
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required; no request sent.")
    asyncio.run(evaluate(args.output))


if __name__ == "__main__":
    main()
