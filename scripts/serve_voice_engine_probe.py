"""One-shot localhost browser codec/Engine voice diagnostic, using synthetic audio only."""
import argparse
import asyncio
import base64
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import logging
import os
from pathlib import Path
import secrets
import threading
import traceback
import uuid
import wave

if __package__:
    from . import check_voice_engine as voice
else:
    import check_voice_engine as voice


def wav_bytes(pcm):
    voice.validate_pcm(pcm)
    target = io.BytesIO()
    with wave.open(target, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(voice.RATE)
        wav.writeframes(pcm)
    return target.getvalue()


def valid_request(headers, *, origin, nonce):
    return (headers.get("Host") == origin.removeprefix("http://")
            and headers.get("Origin") == origin
            and secrets.compare_digest(headers.get("X-Probe-Nonce", ""), nonce))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_live or not os.environ.get("OPENAI_API_KEY"):
        parser.error("Requires --allow-live and injected OPENAI_API_KEY")
    logging.disable(logging.CRITICAL)
    nonce, lock = secrets.token_urlsafe(32), threading.Lock()
    origin = f"http://127.0.0.1:{args.port}"
    state = {"status": "not_started", "calls": [],
             "session_id": "phase0-browser-voice-" + uuid.uuid4().hex[:12],
             "scope": "Synthetic MediaRecorder/codec, hosted voice and chat; no microphone",
             "limitations": ["Automatic approval of exact synthetic fixture by one CLI caller.",
                             "Browser playback events do not prove human listening.",
                             "Browser cancellation does not cancel accepted remote work.",
                             "Both channels recall a previously stored marker."]}

    def save():
        state["recorded_at"] = datetime.now(timezone.utc).isoformat()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(state, indent=2) + "\n")

    async def audio_operation(operation, body):
        from openai import AsyncOpenAI
        async with AsyncOpenAI(timeout=30, max_retries=0) as client:
            if operation == "fixture":
                return await voice.fixture_audio(client)
            return await voice.voice_turn(body, state["session_id"], state["calls"], client)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; media-src blob:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path != "/" or self.headers.get("Host") != origin.removeprefix("http://"):
                return self.send(404, b"{}")
            html = (Path(__file__).parent / "voice_engine_probe.html").read_text()
            self.send(200, html.replace("__PROBE_NONCE__", nonce).encode(), "text/html; charset=utf-8")

        def do_POST(self):
            self.connection.settimeout(15)
            if not valid_request(self.headers, origin=origin, nonce=nonce):
                return self.send(403, b"{}")
            try:
                length = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= length <= voice.MAX_BYTES or self.headers.get("Transfer-Encoding"):
                    raise ValueError("Invalid body size")
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError("Incomplete body")
            except (ValueError, TimeoutError):
                return self.send(400, b"{}")
            if not lock.acquire(blocking=False):
                return self.send(409, b"{}")
            try:
                transitions = {"/fixture": "not_started", "/voice": "fixture_ready",
                               "/chat": "voice_passed", "/playback": "chat_passed"}
                if transitions.get(self.path) != state["status"]:
                    return self.send(409, b"{}")
                if self.path == "/fixture":
                    if body:
                        raise ValueError("Unexpected body")
                    pcm = asyncio.run(audio_operation("fixture", body))
                    state["status"] = "fixture_ready"
                    payload = wav_bytes(pcm)
                    content_type = "audio/wav"
                elif self.path == "/voice":
                    voice.validate_pcm(body)
                    output, lifecycle = asyncio.run(audio_operation("voice", body))
                    state.update(status="voice_passed", lifecycle=lifecycle,
                                 input_pcm_bytes=len(body), output_pcm_bytes=len(output))
                    payload = json.dumps({"status": "voice_passed", "answer": voice.SPOKEN,
                        "wav": base64.b64encode(wav_bytes(output)).decode()}).encode()
                    content_type = "application/json"
                elif self.path == "/chat":
                    if body:
                        raise ValueError("Unexpected body")
                    answer = asyncio.run(voice.engine_turn(state["session_id"], voice.CHAT, state["calls"]))
                    if len({c["execution_id"] for c in state["calls"]}) != 2:
                        raise ValueError("Expected separate voice and chat executions")
                    state["status"] = "chat_passed"
                    payload = json.dumps({"status": "chat_passed", "answer": answer}).encode()
                    content_type = "application/json"
                else:
                    metrics = json.loads(body)
                    if (set(metrics) != {"codec", "encoded_bytes", "playback_ended"}
                            or metrics["codec"] not in ("audio/webm;codecs=opus", "audio/webm", "audio/mp4")
                            or type(metrics["encoded_bytes"]) is not int
                            or not 0 < metrics["encoded_bytes"] <= voice.MAX_BYTES
                            or metrics["playback_ended"] is not True):
                        raise ValueError("Unexpected browser metrics")
                    state.update(status="passed_synthetic_browser_voice_chat", browser_reported=metrics)
                    payload, content_type = b'{"status":"passed_synthetic_browser_voice_chat"}', "application/json"
                save()
                self.send(200, payload, content_type)
            except Exception as error:
                state.update(status="failed_or_incomplete", error_class=type(error).__name__,
                             failure_frames=[{"file": Path(frame.filename).name,
                                              "function": frame.name, "line": frame.lineno}
                                             for frame in traceback.extract_tb(error.__traceback__)[-6:]])
                save()
                self.send(500, b'{"status":"failed_or_incomplete"}')
            finally:
                lock.release()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Synthetic-only probe: {origin}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
