"""Apply only the reviewed UI-3 collection/role proposal after explicit approval."""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from prepare_control_plane_resources import PROJECT, ROLE, atlas, role_consumers, schema

from telecom_app.config import Settings
from telecom_app.database import connect

EXPECTED_SHA256 = "787ce7e4f5adaff4f5b0834ea9d794e6baccbc46ea9c3ca29da492bb83d0d7e2"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-approved-change", action="store_true")
    args = parser.parse_args()
    source = Path("compatibility/ui3-control-plane-proposal.json")
    if hashlib.sha256(source.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Proposal changed; prepare a new review")
    proposal = json.loads(source.read_text())
    expected = {"create": "application_settings", "validator": schema(),
                "validationLevel": "strict", "validationAction": "error"}
    if proposal["create_command"] != expected:
        raise ValueError("Schema differs from reviewed source")
    if atlas("customDbRoles", "describe", ROLE) != proposal["role_before"]:
        raise ValueError("Role drift; no automatic retry")
    consumers, affected_roles = role_consumers()
    if (consumers != proposal["role_consumers"]
            or affected_roles != proposal["affected_role_names"]):
        raise ValueError("Role consumers changed")
    with connect(Settings(os.environ["MONGODB_URI"])) as client:
        db = client.telecom_identity
        if "application_settings" in db.list_collection_names():
            raise ValueError("Collection exists; inspect before resuming")
        if not args.apply_approved_change:
            print("PASS: read-only preflight; no mutation")
            return
        target = Path("compatibility/ui3-control-plane-apply-evidence.json")
        if target.exists():
            raise ValueError("Application evidence exists; no automatic retry")
        evidence = {"status": "started", "proposal_sha256": EXPECTED_SHA256,
                    "collection_created": False, "role_updated": False}
        def save():
            target.write_text(json.dumps(evidence, indent=2) + "\n")
        save()
        try:
            db.command(expected)
            evidence["collection_created"] = True
            options = db.application_settings.options()
            assert all(options.get(key) == expected[key] for key in
                       ("validator", "validationLevel", "validationAction"))
            save()
            body = {key: proposal["role_after"][key] for key in ("actions", "inheritedRoles")}
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as request_file:
                json.dump(body, request_file)
                request_file.flush()
                subprocess.run(["atlas", "api", "customDatabaseRoles", "updateCustomDbRole",
                                "--groupId", PROJECT, "--roleName", ROLE,
                                "--version", "2023-01-01", "--file", request_file.name],
                               capture_output=True, check=True, text=True, timeout=60)
            evidence["role_updated"] = True
            assert atlas("customDbRoles", "describe", ROLE) == proposal["role_after"]
            evidence["status"] = "applied_readback_verified"
        finally:
            save()
    print("Applied only reviewed settings collection and role; runtime remains disabled.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit("Application stopped: " + type(error).__name__) from None
