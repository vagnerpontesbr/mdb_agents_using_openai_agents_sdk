"""Read-only Engine invocation provenance diagnostic; never authorizes a review."""
import argparse
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://agentengine.mongodb.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def assess(profile, response, *, execution, session, workspace, delegated_user):
    """Return only boolean identity comparisons, never personal identifiers/content."""
    if not isinstance(profile, dict) or not isinstance(response, dict):
        return {"status": "blocked", "reason": "invalid_response"}
    runs = response.get("runs")
    if (response.get("truncated") is not False or not isinstance(runs, list)
            or response.get("count") != len(runs)):
        return {"status": "blocked", "reason": "incomplete_run_view",
                "truncated_field_present": "truncated" in response,
                "count_matches_returned_runs": isinstance(runs, list) and response.get("count") == len(runs),
                "returned_run_has_invoker": any(
                    isinstance(r, dict) and r.get("execution_id") == execution
                    and isinstance(r.get("invoker_user_id"), str) and bool(r["invoker_user_id"])
                    for r in (runs if isinstance(runs, list) else []))}
    matches = [r for r in runs if isinstance(r, dict) and r.get("execution_id") == execution]
    if len(matches) != 1:
        return {"status": "blocked", "reason": "execution_not_unique"}
    run = matches[0]
    if run.get("session_id") != session or run.get("workspace_id") != workspace:
        return {"status": "blocked", "reason": "scope_mismatch"}
    caller, invoker = profile.get("user_id"), run.get("invoker_user_id")
    if not all(isinstance(v, str) and v for v in (caller, invoker, run.get("user_id"))):
        return {"status": "blocked", "reason": "identity_missing"}
    checks = {
        "invoker_matches_authenticated_reader": invoker == caller,
        "delegated_user_matches_fixture": run["user_id"] == delegated_user,
        "delegated_user_differs_from_invoker": run["user_id"] != invoker,
    }
    return {"status": "observed" if all(checks.values()) else "blocked", **checks,
            "requester_approval_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("project", "workspace", "session", "execution", "delegated-user"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        credentials = json.loads((Path.home() / ".agentengine/auth.json").read_text())
        token = credentials["credentials"][BASE_URL]["access_token"]
        opener = urllib.request.build_opener(NoRedirect())

        def get(path):
            request = urllib.request.Request(BASE_URL + path, headers={
                "Authorization": "Bearer " + token, "Accept": "application/json"})
            with opener.open(request, timeout=20) as result:
                body = result.read(4_000_001)
            if len(body) > 4_000_000:
                raise ValueError("response too large")
            return json.loads(body)

        profile = get("/api/v1/users/me")
        quote = lambda value: urllib.parse.quote(value, safe="")
        runs = get(f"/api/v1/projects/{quote(args.project)}/sessions/{quote(args.session)}/runs?"
                   + urllib.parse.urlencode({"workspace_id": args.workspace}))
        evidence = assess(profile, runs, execution=args.execution, session=args.session,
                          workspace=args.workspace, delegated_user=args.delegated_user)
    except Exception as error:
        evidence = {"status": "blocked", "error_class": type(error).__name__,
                    "http_status": getattr(error, "code", None)}
    print(json.dumps({"read_only": True, "scope": "original invoker, not current approver",
                      **evidence}, indent=2))
    return 0 if evidence["status"] == "observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
