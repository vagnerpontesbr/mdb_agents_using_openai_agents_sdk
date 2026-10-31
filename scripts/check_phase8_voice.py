"""Three bounded real speech calls overlapping one offline CPU Docling job."""

import argparse
import asyncio
import base64
import io
import json
import os
import signal
import subprocess
import tempfile
import time
import wave
from datetime import UTC, datetime
from pathlib import Path

from telecom_app.voice import VoiceService, pcm_bytes

ROOT = Path(__file__).resolve().parents[1]
TEXT = "Your synthetic invoice total is USD 79.90, due on 2026-12-01."


def audio(data):
    with wave.open(io.BytesIO(data), "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, 24000)
        seconds = wav.getnframes() / 24000
        assert 0.25 <= seconds <= 15
        encoded = base64.b64encode(wav.readframes(wav.getnframes())).decode()
        pcm_bytes(encoded)
    return encoded, seconds


async def run(report, save, directory):
    speech = VoiceService()
    started = time.monotonic()
    report["provider_attempts"] += 1
    save()
    encoded, seconds = audio(await speech.speak(TEXT))
    report["baseline"] = {
        "tts_seconds": round(time.monotonic() - started, 3),
        "audio_seconds": seconds,
    }
    save()
    target = directory / "extracted.json"
    env = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ["HOME"],
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "OMP_NUM_THREADS": "2",
    }
    child = subprocess.Popen(
        [
            str(ROOT / "compatibility/ingestion-runtime/.venv/bin/python"),
            str(ROOT / "scripts/extract_knowledge_pdf.py"),
            str(ROOT / "artifacts/compatibility/pdf/scanned.pdf"),
            "--output",
            str(target),
            "--child",
            "--scanned",
            "--allow-model-downloads",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    began = time.monotonic()

    async def speak():
        tick = time.monotonic()
        report["provider_attempts"] += 1
        save()
        _, duration = audio(await speech.speak(TEXT))
        return {
            "seconds": round(time.monotonic() - tick, 3),
            "audio_seconds": duration,
            "docling_alive_on_completion": child.poll() is None,
        }

    async def transcribe():
        tick = time.monotonic()
        report["provider_attempts"] += 1
        save()
        text = await speech.transcribe(encoded)
        assert "invoice" in text.lower() and "79.90" in text
        return {
            "seconds": round(time.monotonic() - tick, 3),
            "invoice_amount_recognized": True,
            "docling_alive_on_completion": child.poll() is None,
        }

    try:
        tts, stt = await asyncio.gather(speak(), transcribe())
        code = await asyncio.to_thread(child.wait, 120)
        assert code == 0
        extracted = json.loads(target.read_text())
        assert (
            extracted["ocr"] and extracted["pages"] and all(p.strip() for p in extracted["pages"])
        )
        report["contention"] = {
            "tts": tts,
            "stt": stt,
            "docling_seconds": round(time.monotonic() - began, 3),
            "scanned_pages": len(extracted["pages"]),
        }
        assert tts["docling_alive_on_completion"] and stt["docling_alive_on_completion"]
        assert tts["seconds"] <= 45 and stt["seconds"] <= 45
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            await asyncio.to_thread(child.wait)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-live", action="store_true")
    args = parser.parse_args()
    if not args.allow_live:
        print(
            json.dumps(
                {
                    "provider_attempts_max": 3,
                    "retries": 0,
                    "models": ["gpt-4o-mini-tts", "gpt-4o-mini-transcribe"],
                    "scope": "Two short synthetic TTS calls and one STT; no stored audio",
                }
            )
        )
        return 0
    report = {
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
        "provider_attempts": 0,
        "provider_cost_usd": None,
        "thresholds": {"speech_call_seconds": 45, "docling_seconds": 120},
        "limitations": [
            "Synthetic TTS speech, no new human listening acceptance",
            "One overlapping CPU job, not saturated OCR capacity",
            "Provider billing is separate from this latency check",
        ],
    }
    with args.output.open("x") as output:

        def save():
            output.seek(0)
            json.dump(report, output, indent=2)
            output.write("\n")
            output.truncate()
            output.flush()

        save()
        try:
            with tempfile.TemporaryDirectory(prefix="phase8-voice-") as temp:
                asyncio.run(run(report, save, Path(temp)))
            report["status"] = "passed"
        except Exception as error:
            report["status"] = "stopped"
            report["error_type"] = type(error).__name__
        save()
    print(
        json.dumps({"status": report["status"], "provider_attempts": report["provider_attempts"]})
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
