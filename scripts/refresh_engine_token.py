"""Refresh the Engine token through hidden Terminal prompts; never print secrets."""

import base64
import getpass
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request


TOKEN_KEY = "AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"
ENDPOINT = "https://agentengine.mongodb.com/api/v1/oauth/token"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def replace_token(content: str, token: str) -> str:
    if not token or any(c.isspace() for c in token) or any(c in token for c in "\"'#$\\"):
        raise ValueError("Invalid token format")
    lines = content.splitlines(keepends=True)
    positions = [i for i, line in enumerate(lines)
                 if line.strip().split("=", 1)[0].strip() == TOKEN_KEY]
    if len(positions) > 1:
        raise ValueError("Duplicate token configuration")
    replacement = f"{TOKEN_KEY}={token}\n"
    if positions:
        lines[positions[0]] = replacement
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(replacement)
    return "".join(lines)


def write_env(path: Path, content: str) -> None:
    if path.is_symlink():
        raise ValueError("Refusing a symbolic-link env file")
    descriptor, temporary = tempfile.mkstemp(prefix=".engine-env-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    if not sys.stdin.isatty():
        print("Run this command in an interactive Terminal for hidden credential prompts.")
        return 1
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.is_symlink() or not path.is_file():
        print("Expected a regular .env file in the project root.")
        return 1
    original = path.read_text(encoding="utf-8")
    try:
        # Validate the destination before exchanging credentials.
        replace_token(original, "validation-placeholder")
        client_id = getpass.getpass("Engine service account client ID (hidden): ").strip()
        client_secret = getpass.getpass("Engine service account client secret (hidden): ")
        if not client_id or not client_secret or ":" in client_id:
            raise ValueError("Missing or invalid credentials")
        authorization = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        request = urllib.request.Request(
            ENDPOINT,
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={"Authorization": f"Basic {authorization}",
                     "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError("Unexpected response size")
            body = json.loads(raw)
        token = body.get("access_token") if isinstance(body, dict) else None
        if not isinstance(token, str):
            raise ValueError("Missing access token")
        if path.is_symlink() or path.read_text(encoding="utf-8") != original:
            raise ValueError("Env file changed while refreshing")
        write_env(path, replace_token(original, token))
        print("Engine token updated in .env (permissions 0600). No credentials were printed.")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"Token exchange failed: HTTP {exc.code}. The .env file was not updated.")
    except (Exception, KeyboardInterrupt):
        # Do not expose provider bodies, exception text, credentials or token.
        print("Refresh failed or cancelled. Check credentials/connectivity and retry; secret details are suppressed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
