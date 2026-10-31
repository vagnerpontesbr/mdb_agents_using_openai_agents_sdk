"""Prepare isolated load resources offline, reusing authoritative schemas/indexes."""

import argparse
import json
from pathlib import Path

from prepare_phase5_resources import proposal as phase5

from telecom_app.curation_schema import remaining_validators
from telecom_app.knowledge_schema import knowledge_validators

ROOT = Path(__file__).resolve().parents[1]


def proposal():
    previous = json.loads(
        (ROOT / "compatibility/phase4-resource-plan.json").read_text()
    )
    cache = phase5()

    def load_name(name):
        return name.replace("telecom_demo_", "telecom_load_")

    schemas = {load_name(name): value for name, value in remaining_validators().items()}
    schemas.update(
        {
            "telecom_load_knowledge." + name: value
            for name, value in knowledge_validators().items()
        }
    )
    cache_schema = cache["collections"][0]
    schemas["telecom_load_knowledge.retrieval_cache"] = cache_schema["validator"]
    collections = [
        {
            "database": name.split(".")[0],
            "name": name.split(".")[1],
            "validator": value,
            "validationLevel": "strict",
            "validationAction": "error",
        }
        for name, value in sorted(schemas.items())
    ]
    indexes = [*previous["classic_indexes"], *cache["classic_indexes"][:2]]
    searches = [*previous["search_indexes"], cache["search_indexes"][0]]
    for item in indexes + searches:
        item["database"] = load_name(item["database"])
    roles = {}
    users = []
    for role, privileges in previous["runtime_roles"].items():
        name = role.replace("telecom", "telecomLoad", 1)
        roles[name] = [
            {
                **privilege,
                "resource": {
                    **privilege["resource"],
                    "db": load_name(privilege["resource"]["db"]),
                },
            }
            for privilege in privileges
        ]
    for user in previous["runtime_users"]:
        users.append(
            {
                "username": user["username"].replace("telecom_", "telecom_load_", 1),
                "role": user["role"].replace("telecom", "telecomLoad", 1),
            }
        )
    roles["telecomLoadCache"] = [
        {
            "resource": {
                "db": "telecom_load_knowledge",
                "collection": "retrieval_cache",
            },
            "actions": ["find", "insert", "update", "remove"],
        }
    ]
    users.append({"username": "telecom_load_cache", "role": "telecomLoadCache"})
    return {
        "status": "proposed_not_applied",
        "cluster": "OpenAI-SDK",
        "project_id": previous["project_id"],
        "collections": collections,
        "classic_indexes": indexes,
        "search_indexes": searches,
        "runtime_roles": roles,
        "runtime_users": users,
        "estimated_existing_documents_modified": 0,
        "documents_inserted": 0,
        "database_names": ["telecom_load_ingestion", "telecom_load_knowledge"],
        "private_credentials_file": ".env.phase8",
        "unchanged": [
            "demo/evaluation identities and data",
            "ClusterDemoTelco",
            "Engine memory/policies/deployment",
            "Atlas cluster tier",
        ],
        "pending_after_apply": [
            "index readiness",
            "positive and negative role probes",
            "synthetic fixture seeding",
            "worker/lease and source/cache concurrency tests",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x") as output:
        json.dump(proposal(), output, indent=2)
        output.write("\n")
    print("Proposal only; zero external calls or writes.")


if __name__ == "__main__":
    main()
