"""Exact approved LANG-2c batch through domain services; dry preflight by default.

Operator-admitted owner identity, as in check_publication.py; not a browser login test.
Stops on failure without retrying provider calls, deleting evidence or changing IDs.
"""

import argparse
import base64
import hashlib
import json
import os
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

from telecom_app.config import Settings
from telecom_app.curation import OWNER, SCOPE, TENANT, Upload
from telecom_app.curation_runtime import configure
from telecom_app.database import connect
from telecom_app.document_review import request_data
from telecom_app.ingestion_worker import process_pdf
from telecom_app.journey import WORKSPACE, EngineAPI
from telecom_app.knowledge_search import hybrid_pipeline, retrieve
from telecom_app.knowledge_voyage import VoyageKnowledge, post

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "compatibility/lang2c-publication-proposal.json"
DIGEST = "6266f9c071a58a2f72e9f6da938dc8e7064b9966c2c552a4a9e0a872708f52ea"
EVIDENCE = ROOT / "compatibility/lang2c-publication-evidence.json"
TOKEN = "operator-admitted-lang2c"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-approved-change", action="store_true")
    parser.add_argument("--allow-provider-calls", action="store_true")
    args = parser.parse_args()
    if args.apply_approved_change != args.allow_provider_calls:
        parser.error("Both apply and provider authorization flags are required")
    if hashlib.sha256(PROPOSAL.read_bytes()).hexdigest() != DIGEST:
        raise ValueError("Proposal drift")
    proposal = json.loads(PROPOSAL.read_text())
    evidence = {"status": "preflight", "approval": "sim aprovo",
                "proposal_sha256": DIGEST, "started_at": datetime.now(UTC).isoformat(),
                "provider_attempts": {"document": 0, "query": 0, "rerank": 0},
                "sources": [], "stage": "preflight",
                "limitations": ["Operator-admitted owner; not browser authentication",
                                "No hosted deployment, chat, memory or voice acceptance",
                                "Billed cost remains unavailable; USD30 ceiling not increased"]}
    started = time.monotonic()
    clients = []

    def checkpoint():
        if args.apply_approved_change:
            EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n")

    def budget():
        if time.monotonic() - started > 1200:
            raise TimeoutError("Approved 20-minute window expired")

    def transport(base, key, path, payload):
        budget()
        kind = "rerank" if path == "rerank" else payload["input_type"]
        if evidence["provider_attempts"][kind] >= 3:
            raise ValueError("Approved provider cap reached")
        evidence["provider_attempts"][kind] += 1
        checkpoint()  # Count before submission, including uncertain outcomes.
        return post(base, key, path, payload)

    try:
        if args.apply_approved_change and EVIDENCE.exists():
            raise ValueError("Existing batch evidence; inspect before any continuation")
        for name in ("MONGODB_URI", "INGESTION_MONGODB_URI", "KNOWLEDGE_READER_URI",
                     "KNOWLEDGE_PUBLISHER_URI"):
            if urlsplit(os.environ[name]).hostname != "openai-sdk.qrmdk.mongodb.net":
                raise ValueError("Unexpected cluster")
        actor = SimpleNamespace(user_id=None, role="admin")
        identity = SimpleNamespace(principal=lambda token: actor)
        service, clients = configure(identity)
        owner = service.publisher.db.owners.find_one({"tenant_id": TENANT, "owner_id": OWNER,
                                                     "active": True})
        if not owner or len(owner.get("user_ids", [])) != 1:
            raise ValueError("Expected existing single registered owner")
        actor.user_id = owner["user_ids"][0]
        with connect(Settings(mongodb_uri=os.environ["MONGODB_URI"])) as operator:
            validators = json.loads((ROOT / "compatibility/lang2c-validator-proposal.json").read_text())
            for command in validators["commands"]:
                info = next(operator[command["database"]].list_collections(
                    filter={"name": command["collection"]}))
                expected = command["command"]
                options = info["options"]
                if any(options.get(k) != expected[k] for k in (
                        "validator", "validationLevel", "validationAction")):
                    raise ValueError("Validator drift")
        # Native review uses the existing generic metadata contract, not a new deployment.
        workspace = EngineAPI().call("workspaces/" + WORKSPACE)
        workspace = workspace.get("workspace", workspace)
        deployment = workspace.get("current_deployment_id")
        if deployment != "deploy-af009ed4":
            raise ValueError("Unexpected Engine deployment")
        evidence["deployment_id"] = deployment
        uploads = []
        reviewed = datetime.now(UTC).replace(microsecond=0)
        for row in proposal["documents"]:
            budget()
            pdf = (ROOT / row["pdf"]).read_bytes()
            if hashlib.sha256(pdf).hexdigest() != row["checksum"]:
                raise ValueError("Reviewed PDF drift")
            for db, collection in ((service.publisher.db, "documents"),
                                   (service.publisher.db, "document_versions"),
                                   (service.ingestion.db, "jobs")):
                if db[collection].find_one({"tenant_id": TENANT, "document_id": row["document_id"]}):
                    raise ValueError("Document ID already exists")
            data = {k: v for k, v in row.items() if k not in ("pdf", "checksum", "version_key")}
            data.update(pdf_base64=base64.b64encode(pdf).decode(), last_reviewed_at=reviewed)
            upload = Upload.model_validate(data)
            if not upload.effective_from <= reviewed < min(upload.expires_at, upload.review_due_at):
                raise ValueError("Source dates are not currently valid")
            uploads.append(upload)
        print("PASS: exact sources, unused IDs, owner, cluster, validators and Engine read", flush=True)
        if not args.apply_approved_change:
            return
        checkpoint()
        service.voyage = VoyageKnowledge(os.environ["VOYAGE_API_KEY"],
                                         os.environ["VOYAGE_BASE_URL"], transport=transport)

        def wait(execution, desired):
            for _ in range(60):
                budget()
                state = service.review.present(TOKEN, execution)
                if state["status"] == desired:
                    return state
                if state["status"] in ("error", "cancelled", "completed"):
                    raise ValueError("Unexpected native outcome")
                time.sleep(2)
            raise TimeoutError("Native review timeout")

        for row, upload in zip(proposal["documents"], uploads, strict=True):
            budget()
            record = {"document_id": row["document_id"], "language": row["language"]}
            evidence["sources"].append(record)
            evidence["stage"] = "upload"
            checkpoint()
            record["job_id"] = service.upload(TOKEN, upload)["job_id"]
            checkpoint()
            job = service.ingestion.claim(TENANT, record["job_id"])
            if job is None:
                raise ValueError("Exact job not claimable")
            evidence["stage"] = "processing"
            checkpoint()
            staged = process_pdf(service.ingestion.source(job), False, ROOT, service.voyage)
            budget()
            service.ingestion.finish(job, staged)
            _, version = service.job(TOKEN, record["job_id"])
            evidence["stage"] = "native_review"
            checkpoint()
            pending = service.start_review(TOKEN, record["job_id"])
            record["execution_id"] = pending["execution_id"]
            checkpoint()
            pending = wait(record["execution_id"], "suspended")
            if pending["request"] != request_data(record["job_id"], version):
                raise ValueError("Native action differs from uploaded source")
            service.decide(TOKEN, record["execution_id"], pending["action_digest"], "approve")
            final = wait(record["execution_id"], "completed")
            if final["result"]["status"] != "approved":
                raise ValueError("Native approval not granted")
            evidence["stage"] = "publication"
            checkpoint()
            budget()
            published = service.publish(TOKEN, record["execution_id"])
            record.update(published)
            checkpoint()
            if published["version_key"] != row["version_key"]:
                raise ValueError("Published identity mismatch")
            if service.source(TOKEN, row["version_key"]) != (ROOT / row["pdf"]).read_bytes():
                raise ValueError("Published original mismatch")
            print("Published through native approval: " + row["document_id"], flush=True)

        fixture = json.loads((ROOT / "examples/telecom/governance/multilingual/optical-v1.json").read_text())
        evidence["stage"] = "retrieval"
        for source, record, row in zip(fixture["sources"], evidence["sources"], proposal["documents"], strict=True):
            scope = replace(SCOPE, language=source["language"])
            query = source["question"]
            vector = service.voyage.embed_query(query)
            for _ in range(30):
                budget()
                candidates = service.reader.search(hybrid_pipeline(scope, query, vector, datetime.now(UTC)))
                if any(c.version_key == row["version_key"] for c in candidates):
                    break
                time.sleep(2)
            else:
                raise TimeoutError("New source is not searchable")
            answer = retrieve(service.reader, service.publisher, service.voyage, scope, query,
                              vector, max_response_chars=1800)
            if source["document_id"] not in answer:
                raise ValueError("Expected localized citation missing")
            normalized = " ".join(answer.split())
            if not all(" ".join(step.split()) in normalized for step in source["steps"]):
                raise ValueError("Incomplete localized procedure")
            record["all_steps_and_citation_verified"] = True
            for denied in (replace(scope, tenant_id="lang2c-other-tenant"),
                           replace(scope, readers=frozenset({"lang2c-denied"}))):
                if service.reader.search(hybrid_pipeline(denied, query, vector, datetime.now(UTC))):
                    raise ValueError("Tenant or ACL filter bypass")
            record["tenant_acl_denials"] = True
            checkpoint()
            print("PASS: localized source, full steps and tenant/ACL denial: " + source["language"], flush=True)
        evidence["status"] = "passed"
        evidence["stage"] = "complete"
        evidence["elapsed_seconds"] = round(time.monotonic() - started, 2)
        checkpoint()
    except Exception as error:
        evidence.update(status="stopped", error_type=type(error).__name__)
        # Never overwrite a prior execution's evidence on accidental rerun.
        if evidence["sources"] or not EVIDENCE.exists():
            checkpoint()
        print(json.dumps({"status": "stopped", "stage": evidence["stage"],
                          "error_type": type(error).__name__, "details_suppressed": True}))
        raise SystemExit(1) from None
    finally:
        for client in clients:
            client.close()


if __name__ == "__main__":
    main()
