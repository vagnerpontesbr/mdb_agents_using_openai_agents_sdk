"""Demo-only admission before native Engine review; no local approval store."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request
import uuid

from .auth import AccessDenied

BASE = "https://agentengine.mongodb.com"
ORG = "663e3089acf80f05b63effcf"
PROJECT = "67b385a7976edf15ecc62e06"
WORKSPACE = "ws-6ae20f53f3b040aa65fa961a"


class ReviewConflict(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class EngineTransport:
    """Reuse the operator's private CLI login, not a service-account delegation.

    This compatibility transport is intentionally tied to the approved demo
    workspace. Application users never receive this Engine credential.
    """
    def get_execution(self, execution_id):
        credential = json.loads((Path.home() / ".agentengine/auth.json").read_text())
        token = credential["credentials"][BASE]["access_token"]
        url = (f"{BASE}/api/v1/projects/{PROJECT}/executions/"
               f"{urllib.parse.quote(execution_id, safe='')}?workspace_id={WORKSPACE}")
        request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=20) as response:
            body = response.read(1_000_001)
        if len(body) > 1_000_000:
            raise ValueError("Engine response exceeds probe bound")
        result = json.loads(body)
        if result.get("success") is not True:
            raise ValueError("Engine read failed")
        return result["execution"]

    def invoke(self, user, session, *, review=None, decision=None):
        args = ["agentengine", "invoke"]
        if review is None:
            args += ["Read invoice demo-1 and recall my synthetic verification marker."]
        else:
            args += ["--resume", json.dumps({review: {"decision": decision}})]
        args += ["--session", session, "--user-id", user, "--json", "--timeout", "90s",
                 "--base-url", BASE, "--org-id", ORG, "--project-id", PROJECT,
                 "--workspace-id", WORKSPACE, "--no-log"]
        result = subprocess.run(args, capture_output=True, text=True, timeout=100)
        if result.returncode or len(result.stdout) > 1_000_000:
            raise RuntimeError("Engine operation failed; remote outcome may be uncertain")
        response = json.loads(result.stdout)
        if response.get("success") is not True:
            raise RuntimeError("Engine operation did not succeed")
        return response


class EngineReview:
    def __init__(self, sessions, transport):
        self.sessions, self.transport = sessions, transport

    def pending(self, token, execution_id):
        actor = self.sessions.principal(token)
        if not isinstance(execution_id, str) or not re.fullmatch(r"[a-f0-9-]{36}", execution_id):
            raise ValueError("Invalid execution ID")
        execution = self.transport.get_execution(execution_id)
        if any(execution.get(k) != v for k, v in {
                "execution_id": execution_id, "org_id": ORG, "project_id": PROJECT,
                "workspace_id": WORKSPACE}.items()):
            raise ReviewConflict("Engine execution scope mismatch")
        # Original requester comes from Engine state, not browser-submitted IDs.
        if execution.get("user_id") != actor.user_id:
            raise AccessDenied("Only the original requester may approve")
        if execution.get("status") != "suspended":
            raise ReviewConflict("Execution is not awaiting review")
        session = execution.get("session_id")
        if not isinstance(session, str) or not session.startswith("demo-invoice-"):
            raise ReviewConflict("Not a demo invoice session")
        interrupts = execution.get("suspend_context", {}).get("interrupts")
        if not isinstance(interrupts, list) or len(interrupts) != 1:
            raise ReviewConflict("Expected one native pending action")
        interrupt = interrupts[0]
        value, review_id = interrupt.get("value", {}), interrupt.get("id")
        action = value.get("action", {})
        arguments = action.get("arguments", {})
        if (value.get("requesting_user_id") != actor.user_id
                or value.get("contract") != "openai-engine-review-v1"
                or value.get("allowed_decisions") != ["approve", "reject"]
                or not isinstance(review_id, str) or not review_id
                or action.get("tool_name") != "release_synthetic_recall"
                or action.get("tool_call_id") != "release-demo-1"
                or set(arguments) != {"invoice_id", "amount_minor", "currency", "synthetic", "model_reported_marker"}
                or arguments.get("invoice_id") != "demo-1"
                or arguments.get("amount_minor") != 7990 or arguments.get("currency") != "USD"
                or arguments.get("synthetic") is not True
                or not isinstance(arguments.get("model_reported_marker"), str)
                or len(arguments["model_reported_marker"]) > 128):
            raise ReviewConflict("Unexpected pending action")
        projection = {"execution_id": execution_id, "session_id": session, "review_id": review_id,
                      "requester_id": actor.user_id, "action": action,
                      "generation": execution.get("suspend_generation")}
        if type(projection["generation"]) is not int or projection["generation"] < 1:
            raise ReviewConflict("Missing native suspension generation")
        digest = hashlib.sha256(json.dumps(projection, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {**projection, "action_digest": digest}

    def create(self, token):
        actor = self.sessions.principal(token)
        session = "demo-invoice-" + uuid.uuid4().hex
        response = self.transport.invoke(actor.user_id, session)
        pending = self.pending(token, response.get("execution_id"))
        if pending["session_id"] != session:
            raise ReviewConflict("Invocation session mismatch")
        return pending

    def decide(self, token, *, execution_id, action_digest, decision):
        if decision not in ("approve", "reject"):
            raise ValueError("Unsupported decision")
        # Fresh authoritative read and authentication precede ANY native resume.
        pending = self.pending(token, execution_id)
        if action_digest != pending["action_digest"]:
            raise ReviewConflict("Review changed; reload the pending action")
        if self.sessions.principal(token).user_id != pending["requester_id"]:
            raise AccessDenied("Only the original requester may approve")
        response = self.transport.invoke(pending["requester_id"], pending["session_id"],
                                         review=pending["review_id"], decision=decision)
        if (response.get("execution_id") != execution_id
                or response.get("session_id") != pending["session_id"] or response.get("suspended")):
            raise ReviewConflict("Unexpected resume result")
        result = json.loads(response.get("response", "null"))
        expected = pending["action"]["arguments"] if decision == "approve" else {
            "status": "rejected", "tool_call_id": "release-demo-1"}
        if result != expected:
            raise ReviewConflict("Unexpected final output")
        return {"execution_id": execution_id, "result": result}
