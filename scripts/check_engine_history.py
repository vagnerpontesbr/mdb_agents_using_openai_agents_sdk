"""Bounded read-only Engine history availability probe; not an SDK adapter proof."""
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://agentengine.mongodb.com"
MAX_BYTES = 1_000_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def assess(response, *, session):
    """Expect a known completed synthetic session with at least one message.

    Report structure only. Even an observed transcript needs a separate proof
    of lossless SDK translation and Engine replay before runtime integration.
    """
    blocked = lambda reason: {"status": "blocked", "reason": reason}
    if not isinstance(response, dict):
        return blocked("invalid_response")
    if response.get("history_status") != "ready":
        return blocked("history_not_ready")
    if response.get("latest_status") != "completed":
        return blocked("session_not_completed")
    if response.get("outcome_supported") is not True:
        return blocked("outcome_classification_unavailable")
    messages = response.get("messages")
    if not isinstance(messages, list):
        return blocked("invalid_messages")
    if not messages:
        return blocked("completed_session_has_no_history")
    if len(messages) > 100:
        return blocked("history_exceeds_probe_bound")
    roles = []
    for message in messages:
        if not isinstance(message, dict) or message.get("session_id") != session:
            return blocked("message_scope_mismatch")
        if message.get("outcome") not in (None, ""):
            return blocked("non_success_outcome_requires_semantics")
        role = message.get("role")
        if role not in ("user", "assistant", "tool"):
            return blocked("unsupported_or_privileged_role")
        roles.append(role)
    return {"status": "observed", "message_count": len(messages), "roles": roles,
            "sdk_restoration_proven": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("project", "workspace", "session"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        token = os.environ["AGENT_ENGINE_SERVICE_ACCOUNT_TOKEN"]
        quote = lambda value: urllib.parse.quote(value, safe="")
        url = (f"{BASE_URL}/api/v1/projects/{quote(args.project)}/sessions/"
               f"{quote(args.session)}/messages?"
               + urllib.parse.urlencode({"workspace_id": args.workspace}))
        request = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token, "Accept": "application/json"})
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(request, timeout=30) as result:
            body = result.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("response exceeds probe bound")
        evidence = assess(json.loads(body), session=args.session)
    except Exception as error:
        evidence = {"status": "blocked", "error_class": type(error).__name__,
                    "http_status": getattr(error, "code", None)}
    print(json.dumps({"read_only": True, **evidence}, indent=2))
    return 0 if evidence["status"] == "observed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
