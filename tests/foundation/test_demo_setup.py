"""Setup diagnostics must not reveal private configuration values."""

import json

from scripts.check_demo_setup import configuration_checks


def test_setup_report_contains_names_not_secret_values(tmp_path):
    secret = "do-not-print-this-private-value"
    env = dict.fromkeys(("APP_MONGODB_URI", "APP_ORIGIN", "APP_WEB_DIST"), secret)
    env["APP_MONGODB_HOST"] = "openai-sdk.qrmdk.mongodb.net"
    rows = configuration_checks(env, tmp_path)
    assert all(row["ok"] for row in rows)
    assert secret not in json.dumps(rows)


def test_knowledge_setup_requires_scoped_identities_and_cli_is_not_implied(tmp_path):
    rows = configuration_checks({"APP_JOURNEY_ENABLED": "true",
                                 "APP_KNOWLEDGE_ENABLED": "true"}, tmp_path)
    missing = {row["check"] for row in rows if not row["ok"]}
    assert {"private_engine_cli_login_file", "INGESTION_MONGODB_URI",
            "KNOWLEDGE_PUBLISHER_URI", "KNOWLEDGE_READER_URI"} <= missing
