"""Browser-test fixture only: synthetic accounts, in-memory store, no provider calls."""

import os
from pathlib import Path

import uvicorn

from compatibility.demo_auth.sessions import SessionAuth
from telecom_app.api import create_app
from telecom_app.config import Settings
from tests.demo_auth.test_sessions import SessionStore

if __name__ == "__main__":
    port = int(os.environ.get("TELECOM_TEST_PORT", "53181"))
    auth = SessionAuth(SessionStore())
    auth.auth.bootstrap("synthetic-browser-only")
    settings = Settings(
        "mongodb+srv://synthetic:synthetic@openai-sdk.qrmdk.mongodb.net/",
        origin=f"http://127.0.0.1:{port}", web_dist=Path("apps/web/dist").resolve(),
    )
    uvicorn.run(create_app(settings, auth), host="127.0.0.1", port=port,
                access_log=False, proxy_headers=False)
