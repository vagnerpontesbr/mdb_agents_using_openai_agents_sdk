"""Storage contracts for the remaining approved curation/ingestion collections."""

from typing import Any


def remaining_validators() -> dict[str, dict[str, Any]]:
    string = {"bsonType": "string", "minLength": 1, "maxLength": 128}
    digest = {"bsonType": "string", "pattern": "^[a-f0-9]{64}$"}
    integer = {"bsonType": ["int", "long"], "minimum": 0}
    date = {"bsonType": "date"}

    def schema(fields: dict[str, Any], optional: tuple[str, ...] = ()) -> dict[str, Any]:
        return {"bsonType": "object", "additionalProperties": False,
                "required": [key for key in fields if key not in optional], "properties": fields}

    documents = schema({"_id": digest, "tenant_id": string, "document_id": string,
                        "version_key": digest, "version_id": string,
                        "revision": {**integer, "minimum": 1}, "conflict": {"bsonType": "bool"}})
    owners = schema({"_id": {"bsonType": "string", "maxLength": 300}, "tenant_id": string,
                     "owner_id": string, "active": {"bsonType": "bool"},
                     "user_ids": {"bsonType": "array", "minItems": 1, "maxItems": 16,
                                  "uniqueItems": True, "items": string}})
    receipts = schema({"_id": digest, "tenant_id": string, "execution_id": string,
        "action_digest": digest, "version_key": digest, "metadata_digest": digest,
        "actor": string, "source_checksum": digest, "job_id": digest, "recorded_at": date})
    jobs = schema({"_id": digest, "tenant_id": string, "submission_key": digest,
        "document_id": string, "version_id": string, "metadata_digest": digest,
        "checksum": digest, "scanned": {"bsonType": "bool"},
        "status": {"enum": ["queued", "running", "staged", "failed"]},
        "attempts": {**integer, "maximum": 2}, "available_at": date, "created_at": date,
        "lease_token": {"bsonType": ["string", "null"]}, "lease_until": date,
        "failure": {"enum": [None, "invalid_document", "provider_failure", "worker_failure"]},
        "metadata": {"bsonType": ["object", "null"]}, "finished_at": date},
        ("finished_at", "metadata"))
    quota = schema({"_id": {"bsonType": "string", "maxLength": 140}, "tenant_id": string,
                    "kind": {"enum": ["quota"]}, "active": {**integer, "maximum": 4}})
    artifact = schema({"_id": digest, "tenant_id": string, "kind": {"enum": ["pdf"]},
        "pdf": {"bsonType": "binData"}, "checksum": digest, "created_at": date,
        "result": {"bsonType": "object"}}, ("result",))
    return {
        "telecom_demo_knowledge.documents": {"$jsonSchema": documents},
        "telecom_demo_knowledge.owners": {"$jsonSchema": owners},
        "telecom_demo_knowledge.review_events": {"$jsonSchema": receipts},
        "telecom_demo_ingestion.jobs": {"$and": [{"$jsonSchema": jobs},
            {"$expr": {"$lte": [{"$bsonSize": "$$ROOT"}, 16000]}}]},
        "telecom_demo_ingestion.staged_artifacts": {"$and": [
            {"$jsonSchema": {"oneOf": [quota, artifact]}},
            {"$expr": {"$lte": [{"$bsonSize": "$$ROOT"}, 7000000]}}]},
    }
