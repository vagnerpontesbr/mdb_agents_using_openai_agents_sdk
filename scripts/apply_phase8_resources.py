"""Apply only the reviewed isolated load plan; default is a zero-call dry run."""

import argparse
import hashlib
import json
import os
import secrets
import subprocess
from urllib.parse import urlsplit

from apply_knowledge_resources import atlas, normalized_actions, role_actions
from prepare_phase8_resources import ROOT, proposal
from pymongo import MongoClient
from pymongo.operations import SearchIndexModel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-sha256")
    args = parser.parse_args()
    path = ROOT / "compatibility/phase8-resource-plan.json"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    plan = json.loads(raw)
    if plan != proposal():
        raise ValueError("Source/plan drift; regenerate and review")
    if args.approved_sha256 is None:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "plan_sha256": digest,
                    "external_calls": 0,
                    "collections": len(plan["collections"]),
                    "search_indexes": len(plan["search_indexes"]),
                    "roles": list(plan["runtime_roles"]),
                    "users": [u["username"] for u in plan["runtime_users"]],
                }
            )
        )
        return
    if args.approved_sha256 != digest:
        raise ValueError("Approval does not match the exact plan")
    uri = os.environ["MONGODB_URI"]
    if urlsplit(uri).hostname != "openai-sdk.qrmdk.mongodb.net":
        raise ValueError("Unexpected provisioning cluster")
    private = ROOT / ".env.phase8"
    if private.is_symlink() or private.exists() and private.stat().st_mode & 0o077:
        raise ValueError("Private credentials must be a non-symlink mode-0600 file")
    if subprocess.run(["git", "check-ignore", "-q", str(private)], cwd=ROOT).returncode:
        raise ValueError("Credential path must be ignored")
    credentials = (
        dict(line.split("=", 1) for line in private.read_text().splitlines() if line)
        if private.exists()
        else {}
    )
    project = plan["project_id"]
    roles = {
        r["roleName"]: r
        for r in atlas("customDatabaseRoles", "listCustomDbRoles", project)
    }
    inventory = atlas("databaseUsers", "listDatabaseUsers", project)
    if inventory.get("totalCount", len(inventory["results"])) != len(
        inventory["results"]
    ):
        raise ValueError("User inventory requires pagination")
    users = {u["username"]: u for u in inventory["results"]}
    for name, privileges in plan["runtime_roles"].items():
        if name in roles and (
            roles[name].get("inheritedRoles")
            or normalized_actions(roles[name]["actions"])
            != normalized_actions(role_actions(privileges))
        ):
            raise ValueError("Load role drift")
    for user in plan["runtime_users"]:
        name = user["username"]
        if name in users and (
            name not in credentials
            or users[name]["roles"]
            != [{"roleName": user["role"], "databaseName": "admin"}]
            or users[name].get("scopes") != [{"name": "OpenAI-SDK", "type": "CLUSTER"}]
        ):
            raise ValueError("Load user drift or unavailable credential")
    # One reused client, sequential provisioning, existing 15-second operation budget.
    # No production pool settings or cluster capacity are changed by this admin task.
    with MongoClient(
        uri, timeoutMS=15000, appname="telecom-phase8-provision"
    ) as client:
        absent = []
        classic = []
        search = []
        for item in plan["collections"]:
            db = client[item["database"]]
            found = list(db.list_collections(filter={"name": item["name"]}))
            options = {
                k: item[k] for k in ("validator", "validationLevel", "validationAction")
            }
            if found:
                if any(
                    found[0].get("options", {}).get(k) != v for k, v in options.items()
                ):
                    raise ValueError("Load validator drift")
            else:
                absent.append(item)
        for item in plan["classic_indexes"]:
            collection = client[item["database"]][item["collection"]]
            found = collection.index_information().get(item["name"])
            if found:
                if (
                    found["key"] != list(item["key"].items())
                    or bool(found.get("unique")) != bool(item.get("unique"))
                    or found.get("expireAfterSeconds") != item.get("expireAfterSeconds")
                ):
                    raise ValueError("Load index drift")
            else:
                classic.append(item)
        for item in plan["search_indexes"]:
            exists = any(
                x["database"] == item["database"] and x["name"] == item["collection"]
                for x in absent
            )
            found = (
                []
                if exists
                else list(
                    client[item["database"]][item["collection"]].list_search_indexes(
                        item["name"]
                    )
                )
            )
            if found:
                if (
                    found[0]["latestDefinition"] != item["definition"]
                    or found[0]["type"] != item["type"]
                ):
                    raise ValueError("Load search index drift")
            else:
                search.append(item)
        # All drift checks complete before the first remote mutation.
        for item in absent:
            client[item["database"]].create_collection(
                item["name"],
                **{
                    k: item[k]
                    for k in ("validator", "validationLevel", "validationAction")
                },
            )
        for item in classic:
            client[item["database"]][item["collection"]].create_index(
                list(item["key"].items()),
                **{
                    k: item[k]
                    for k in ("name", "unique", "expireAfterSeconds")
                    if k in item
                },
            )
        for item in search:
            client[item["database"]][item["collection"]].create_search_index(
                SearchIndexModel(
                    name=item["name"], definition=item["definition"], type=item["type"]
                )
            )
        for name, privileges in plan["runtime_roles"].items():
            if name not in roles:
                atlas(
                    "customDatabaseRoles",
                    "createCustomDbRole",
                    project,
                    {
                        "roleName": name,
                        "actions": role_actions(privileges),
                        "inheritedRoles": [],
                    },
                )
        for user in plan["runtime_users"]:
            name = user["username"]
            if name in users:
                continue
            if name not in credentials:
                credentials[name] = secrets.token_urlsafe(36)
                fd = os.open(
                    private,
                    os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
                    0o600,
                )
                with os.fdopen(fd, "w") as output:
                    output.write(
                        "".join(
                            f"{key}={value}\n" for key, value in credentials.items()
                        )
                    )
            atlas(
                "databaseUsers",
                "createDatabaseUser",
                project,
                {
                    "databaseName": "admin",
                    "username": name,
                    "password": credentials[name],
                    "roles": [{"roleName": user["role"], "databaseName": "admin"}],
                    "scopes": [{"name": "OpenAI-SDK", "type": "CLUSTER"}],
                },
            )
    evidence = {
        "status": "applied_readiness_and_roles_unverified",
        "plan_sha256": digest,
        "collections_created": len(absent),
        "classic_indexes_created": len(classic),
        "search_indexes_created": len(search),
        "pending": plan["pending_after_apply"],
    }
    (ROOT / "compatibility/phase8-resource-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n"
    )
    print(json.dumps(evidence))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "stopped", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
