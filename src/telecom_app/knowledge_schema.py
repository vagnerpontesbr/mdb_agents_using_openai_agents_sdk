"""MongoDB storage validators derived from the authoritative version/candidate contracts."""

from typing import Any

from .knowledge import Version
from .knowledge_search import DIMENSIONS, PROFILE, Candidate


def bson_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Translate only the JSON Schema subset used by these two pinned Pydantic models."""
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key in {"title", "default"}:
            continue
        if key == "type":
            result["bsonType"] = {"integer": ["int", "long"], "number": "double",
                                  "boolean": "bool"}.get(value, value)
        elif key == "format" and value == "date-time":
            result["bsonType"] = "date"
        elif key == "const":
            result["enum"] = [value]
        elif key == "properties":
            result[key] = {name: bson_schema(item) for name, item in value.items()}
        elif key == "items":
            result[key] = bson_schema(value)
        elif key == "anyOf":
            result[key] = [bson_schema(item) for item in value]
        elif key in {"required", "additionalProperties", "minLength", "maxLength",
                     "minItems", "maxItems", "minimum", "maximum", "pattern", "enum"}:
            result[key] = value
        else:
            raise ValueError(f"Unsupported storage schema keyword: {key}")
    if schema.get("format") == "date-time":
        result["bsonType"] = "date"
    return result


def knowledge_validators() -> dict[str, dict[str, Any]]:
    version = bson_schema(Version.model_json_schema())
    key = {"bsonType": "string", "minLength": 1, "maxLength": 128}
    version["properties"]["_id"] = key
    version["required"].append("_id")
    version["properties"]["acl"]["items"] = key
    chronology = [("created_at", "effective_from", "$lte"),
                  ("effective_from", "expires_at", "$lt"),
                  ("created_at", "last_reviewed_at", "$lte"),
                  ("last_reviewed_at", "review_due_at", "$lt"),
                  ("created_at", "approved_at", "$lte"),
                  ("created_at", "ingested_at", "$lte")]
    chunk = bson_schema(Candidate.model_json_schema())
    chunk["properties"].update({"_id": {}, "tenant_id": key,
        **{name: version["properties"][name] for name in
           ("acl", "product", "region", "firmware_range", "language", "status",
            "effective_from", "expires_at", "review_due_at")},
        "embedding_profile": {"enum": [PROFILE]}, "eligible": {"bsonType": "bool"},
        "embedding": {"bsonType": "array", "minItems": DIMENSIONS, "maxItems": DIMENSIONS,
                      "items": {"bsonType": "double", "minimum": -1e308, "maximum": 1e308}},
    })
    chunk["properties"]["pages"].update(uniqueItems=True, items={
        "bsonType": ["int", "long"], "minimum": 1, "maximum": 10})
    chunk["required"] = list(chunk["properties"])
    return {
        "document_versions": {"$and": [{"$jsonSchema": version}, {"$expr": {"$and": [
            {op: ["$" + left, "$" + right]} for left, right, op in chronology]}}]},
        "chunks": {"$jsonSchema": chunk},
    }
