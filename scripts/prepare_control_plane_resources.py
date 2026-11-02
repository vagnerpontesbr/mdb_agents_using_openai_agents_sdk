"""Read-only Atlas inventory and exact application settings resource proposal."""
import copy
import hashlib
import json
import subprocess
from pathlib import Path

PROJECT = "67b385a7976edf15ecc62e06"
ROLE = "telecomDemoIdentityRuntime"


def atlas(*args):
    result = subprocess.run(["atlas", *args, "--projectId", PROJECT, "--output", "json"],
                            capture_output=True, text=True, check=True, timeout=45)
    return json.loads(result.stdout)



def role_consumers():
    roles = atlas("customDbRoles", "list")
    affected = {ROLE}
    while True:
        expanded = affected | {row["roleName"] for row in roles if any(
            parent.get("role") in affected and parent.get("db") == "admin"
            for parent in row.get("inheritedRoles", []))}
        if expanded == affected:
            break
        affected = expanded
    users = atlas("dbusers", "list")["results"]
    consumers = [{"username": row["username"], "scopes": row.get("scopes", [])}
                 for row in users if any(role["roleName"] in affected for role in row["roles"])]
    return sorted(consumers, key=lambda row: row["username"]), sorted(affected)


def schema():
    integer = lambda lo, hi: {"bsonType": ["int", "long"], "minimum": lo, "maximum": hi}
    values = {"bsonType": "object", "additionalProperties": False,
              "required": ["chat_max_chars", "knowledge_query_max_chars",
                           "library_cache_max_age_seconds"],
              "properties": {"chat_max_chars": integer(100, 4000),
                             "knowledge_query_max_chars": integer(100, 2000),
                             "library_cache_max_age_seconds": integer(1, 900)}}
    revision = {"bsonType": ["int", "long"], "minimum": 1}
    event = {"bsonType": "object", "additionalProperties": False,
             "required": ["revision", "actor_id", "at", "before", "after"],
             "properties": {"revision": revision, "actor_id": {"bsonType": "string",
                            "maxLength": 128}, "at": {"bsonType": "date"},
                            "before": values, "after": values}}
    return {"$jsonSchema": {"bsonType": "object", "additionalProperties": False,
            "required": ["_id", "revision", "values", "audit"],
            "properties": {"_id": {"enum": ["application"]}, "revision": revision,
                           "values": values, "audit": {"bsonType": "array", "minItems": 1,
                                                       "maxItems": 20, "items": event}}}}


def main():
    before = atlas("customDbRoles", "describe", ROLE)
    consumers, affected_roles = role_consumers()
    resource = {"cluster": False, "db": "telecom_identity", "collection": "application_settings"}
    after = copy.deepcopy(before)
    for action in ("FIND", "INSERT", "UPDATE"):
        entry = next(row for row in after["actions"] if row["action"] == action)
        if resource in entry["resources"]:
            raise ValueError("Settings privilege already exists; inspect drift")
        entry["resources"].append(resource)
    proposal = {"status": "proposal_not_applied", "project_id": PROJECT, "cluster": "OpenAI-SDK",
                "host": "openai-sdk.qrmdk.mongodb.net", "database": "telecom_identity",
                "collection": "application_settings", "expected_collection": "absent",
                "role_consumers": consumers, "affected_role_names": affected_roles, "role_before": before, "role_after": after,
                "create_command": {"create": "application_settings", "validator": schema(),
                                   "validationLevel": "strict", "validationAction": "error"},
                "existing_documents_modified": 0, "initial_documents_inserted": 0,
                "new_indexes": 0, "engine_changes": False,
                "rollback": "Disable APP_CONTROL_PLANE_ENABLED on new application starts; "
                "restore exact role_before after reviewing consumers; retain collection and audit."}
    out = Path("compatibility/ui3-control-plane-proposal.json")
    out.write_text(json.dumps(proposal, indent=2) + "\n")
    print(json.dumps({"proposal": str(out), "consumers": consumers,
                      "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit("Read-only proposal preparation failed: " + type(error).__name__) from None
