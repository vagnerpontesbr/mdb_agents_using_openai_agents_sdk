"""Isolated HTTP load fixture. Identity and Engine are doubles, never production owners.

SQLite is solely the external Engine double's shared state across API processes.
No credentials, database connection, LLM, voice provider or SDK execution is used.
"""

import asyncio
import io
import json
import os
import sqlite3
import time
import wave
from uuid import uuid4

from compatibility.demo_auth.auth import AccessDenied, Principal
from telecom_app.api import create_app
from telecom_app.config import Settings
from telecom_app.journey import (
    ORG,
    PROJECT,
    WORKSPACE,
    EngineAPI,
    EngineUnavailable,
    JourneyService,
)
from telecom_app.voice import pcm_bytes


class VoiceDouble:
    """Validate real PCM/WAV transport with a tone, without claiming speech quality."""

    async def transcribe(self, encoded):
        pcm_bytes(encoded)
        await asyncio.sleep(0.05)
        return "Synthetic transport request."

    async def speak(self, text):
        if text != "Synthetic transport response.":
            raise ValueError("Unexpected synthetic speech source")
        await asyncio.sleep(0.05)
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            wav.writeframes(b"\x00\x04\x00\xfc" * 3000)
        return output.getvalue()


class IdentityDouble:
    def principal(self, token):
        if token not in ("load-a", "load-b"):
            raise AccessDenied("Login required")
        return Principal(token, token + "@example.invalid", "user")


class EngineDouble(EngineAPI):
    def invoke(self, user, session, message):
        if message == "injected-unavailable":
            raise EngineUnavailable("Synthetic unavailable provider")
        time.sleep(0.05)
        execution = str(uuid4())
        row = {
            "execution_id": execution,
            "user_id": user,
            "session_id": session,
            "org_id": ORG,
            "project_id": PROJECT,
            "workspace_id": WORKSPACE,
            "status": "completed",
            "result": {
                "contract": "telecom-journey-v1",
                "status": "completed",
                "text": "Synthetic transport response.",
                "specialists": ["financial"],
            },
        }
        with sqlite3.connect(os.environ["TELECOM_LOAD_STATE"], timeout=5) as store:
            store.execute(
                "INSERT INTO executions VALUES (?, ?, ?)",
                (execution, session, json.dumps(row)),
            )
        return {"execution_id": execution}

    def execution(self, execution):
        with sqlite3.connect(os.environ["TELECOM_LOAD_STATE"], timeout=5) as store:
            row = store.execute(
                "SELECT body FROM executions WHERE id = ?", (execution,)
            ).fetchone()
        if row is None:
            raise EngineUnavailable("Synthetic execution absent")
        return json.loads(row[0])

    def latest(self, session):
        with sqlite3.connect(os.environ["TELECOM_LOAD_STATE"], timeout=5) as store:
            row = store.execute(
                "SELECT id FROM executions WHERE session = ? ORDER BY rowid DESC LIMIT 1",
                (session,),
            ).fetchone()
        return row[0] if row else None


def application():
    if os.environ.get("TELECOM_LOAD_FIXTURE") != "isolated-mock-v1":
        raise RuntimeError("Explicit load fixture required")
    identity = IdentityDouble()
    settings = Settings(
        mongodb_uri="mongodb+srv://synthetic:unused@openai-sdk.qrmdk.mongodb.net/",
        origin=os.environ["TELECOM_LOAD_ORIGIN"],
    )
    app = create_app(
        settings,
        identity=identity,
        journey=JourneyService(identity, EngineDouble()),
        voice=VoiceDouble() if os.environ.get("TELECOM_LOAD_VOICE") == "true" else None,
    )

    @app.get("/_load/metrics")
    async def metrics():
        started = time.perf_counter()
        await asyncio.sleep(0.01)
        return {
            "pid": os.getpid(),
            "loop_lag_ms": max(0, (time.perf_counter() - started - 0.01) * 1000),
        }

    @app.middleware("http")
    async def process_identity(request, call_next):
        response = await call_next(request)
        response.headers["X-Load-Process"] = str(os.getpid())
        return response

    return app
