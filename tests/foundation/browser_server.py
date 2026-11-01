"""Browser-test fixture only: synthetic accounts, in-memory store, no provider calls."""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import uvicorn

from compatibility.demo_auth.sessions import SessionAuth, token_digest
from telecom_app.api import create_app
from telecom_app.config import Settings
from tests.demo_auth.test_sessions import SessionStore

if __name__ == "__main__":
    port = int(os.environ.get("TELECOM_TEST_PORT", "53181"))
    auth = SessionAuth(SessionStore())
    auth.auth.bootstrap("synthetic-browser-only")
    # Fixture-only user/session for password tests; avoids exhausting the real peer limiter.
    password_user = auth.auth._insert(
        "password-probe@example.test", "synthetic-password-before", "user",
    )
    auth.store.insert_session({"_id": token_digest("p" * 43), "email": password_user.email,
                               "user_id": password_user.user_id, "credential_version": 0,
                               "expires_at": datetime.now(UTC) + timedelta(hours=1)})
    settings = Settings(
        "mongodb+srv://synthetic:synthetic@openai-sdk.qrmdk.mongodb.net/",
        origin=f"http://127.0.0.1:{port}", web_dist=Path("apps/web/dist").resolve(),
    )
    uvicorn.run(create_app(settings, auth), host="127.0.0.1", port=port,
                access_log=False, proxy_headers=False)
