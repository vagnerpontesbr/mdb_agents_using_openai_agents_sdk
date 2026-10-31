"""Verify load roles and demo denial using aborted synthetic transactions."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import OperationFailure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("compatibility/phase8-role-evidence.json"))
    args = parser.parse_args()
    plan = json.loads(Path("compatibility/phase8-resource-plan.json").read_text())
    credentials = dict(
        line.split("=", 1)
        for line in Path(".env.phase8").read_text().splitlines()
        if line
    )
    namespaces = [(c["database"], c["name"]) for c in plan["collections"]]
    probes = namespaces + [
        ("telecom_identity", "users"),
        ("telecom_demo_ingestion", "jobs"),
        ("telecom_demo_knowledge", "document_versions"),
    ]
    report = {
        "status": "running",
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": [],
        "limitations": [
            "Schema rejection proves authorization, not valid document insertion",
            "Tenant/ACL isolation requires separate domain tests",
        ],
    }
    output = args.output.open("x")

    def save():
        output.seek(0)
        json.dump(report, output, indent=2)
        output.write("\n")
        output.truncate()
        output.flush()

    save()
    try:
        for user in plan["runtime_users"]:
            allowed = {
                (p["resource"]["db"], p["resource"]["collection"]): p["actions"]
                for p in plan["runtime_roles"][user["role"]]
            }
            # Sequential probes: one reused client, one operation, no prewarmed pool.
            with MongoClient(
                "mongodb+srv://openai-sdk.qrmdk.mongodb.net/",
                username=user["username"],
                password=credentials[user["username"]],
                authSource="admin",
                maxPoolSize=1,
                minPoolSize=0,
                timeoutMS=15000,
                appname="telecom-phase8-role-probe",
            ) as client:
                for db, coll in probes:
                    for action in ("find", "insert", "update", "remove"):
                        permitted = False
                        schema_rejected = False
                        with client.start_session() as session:
                            session.start_transaction()
                            try:
                                target = client[db][coll]
                                marker = uuid4().hex * 2
                                if action == "find":
                                    target.find_one({"_id": marker}, session=session)
                                elif action == "insert":
                                    target.insert_one({"_id": marker}, session=session)
                                elif action == "update":
                                    target.update_one(
                                        {"_id": marker},
                                        {"$set": {"tenant_id": "load-probe"}},
                                        session=session,
                                    )
                                else:
                                    target.delete_one({"_id": marker}, session=session)
                                permitted = True
                            except OperationFailure as error:
                                if error.code == 121 and action == "insert":
                                    permitted = True
                                    schema_rejected = True
                                elif error.code != 13:
                                    raise
                            finally:
                                session.abort_transaction()
                        assert permitted == (action in allowed.get((db, coll), []))
                        report["checks"].append(
                            {
                                "user": user["username"],
                                "namespace": f"{db}.{coll}",
                                "action": action,
                                "allowed": permitted,
                                "schema_rejected": schema_rejected,
                            }
                        )
                print(json.dumps({"identity_verified": user["username"]}), flush=True)
                save()
        for key in ("KNOWLEDGE_READER_URI", "INGESTION_MONGODB_URI"):
            with MongoClient(
                os.environ[key],
                maxPoolSize=1,
                minPoolSize=0,
                timeoutMS=15000,
                appname="telecom-phase8-demo-denial",
            ) as client:
                for db, coll in namespaces:
                    for action in ("find", "insert"):
                        with client.start_session() as session:
                            session.start_transaction()
                            try:
                                if action == "find":
                                    client[db][coll].find_one(
                                        {"_id": uuid4().hex}, session=session
                                    )
                                else:
                                    client[db][coll].insert_one(
                                        {"_id": uuid4().hex}, session=session
                                    )
                            except OperationFailure as error:
                                assert error.code == 13
                            else:
                                raise AssertionError(
                                    "Demo identity accessed load namespace"
                                )
                            finally:
                                session.abort_transaction()
                        report["checks"].append(
                            {
                                "identity_config": key,
                                "namespace": f"{db}.{coll}",
                                "action": action,
                                "allowed": False,
                            }
                        )
            save()
        with MongoClient(
            os.environ["MONGODB_URI"], maxPoolSize=1, minPoolSize=0, timeoutMS=15000
        ) as client:
            report["indexes"] = []
            for item in plan["collections"]:
                info = list(
                    client[item["database"]].list_collections(
                        filter={"name": item["name"]}
                    )
                )[0]
                assert all(
                    info["options"].get(k) == item[k]
                    for k in ("validator", "validationLevel", "validationAction")
                )
            for item in plan["search_indexes"]:
                rows = list(
                    client[item["database"]][item["collection"]].list_search_indexes(
                        item["name"]
                    )
                )
                assert len(rows) == 1
                row = rows[0]
                assert row["latestDefinition"] == item["definition"]
                report["indexes"].append(
                    {
                        "namespace": item["database"] + "." + item["collection"],
                        "name": row["name"],
                        "status": row["status"],
                        "queryable": row["queryable"],
                    }
                )
            report["status"] = (
                "passed"
                if all(
                    i["status"] == "READY" and i["queryable"] for i in report["indexes"]
                )
                else "awaiting_index_readiness"
            )
    except Exception as error:
        report["status"] = "stopped"
        report["error_type"] = type(error).__name__
        report["error_code"] = getattr(error, "code", None)
    finally:
        save()
        output.close()
    print(
        json.dumps(
            {
                "status": report["status"],
                "role_checks": len(report["checks"]),
                "indexes": report.get("indexes", []),
            }
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
