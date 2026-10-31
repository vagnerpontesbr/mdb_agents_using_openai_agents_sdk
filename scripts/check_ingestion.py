"""Bounded live staging proof with a synthetic PDF and scoped ingestion identity."""

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from pymongo import MongoClient

from telecom_app.ingestion import IngestionConflict, MongoIngestion
from telecom_app.ingestion_worker import process_pdf
from telecom_app.knowledge_voyage import VoyageKnowledge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-provider-calls', action='store_true', required=True)
    parser.parse_args()
    if urlsplit(os.environ['MONGODB_URI']).hostname != 'openai-sdk.qrmdk.mongodb.net':
        raise ValueError('Unexpected operator cluster')
    tenant = 'synthetic-ingestion-' + uuid4().hex
    credentials = dict(line.split('=', 1) for line in
                       Path('.env.phase4').read_text().splitlines() if line)
    now = [datetime.now(UTC)]
    checks = []
    pdf = Path('artifacts/compatibility/pdf/text.pdf').read_bytes()
    with MongoClient(os.environ['MONGODB_URI'], timeoutMS=15000,
                     appname='telecom-ingestion-probe-cleanup') as operator, MongoClient(
            'mongodb+srv://openai-sdk.qrmdk.mongodb.net/', username='telecom_ingestion_worker',
            password=credentials['telecom_ingestion_worker'], authSource='admin',
            timeoutMS=15000, appname='telecom-ingestion-probe') as client:
        store = MongoIngestion(client.telecom_demo_ingestion, clock=lambda: now[0])
        try:
            with ThreadPoolExecutor(max_workers=4) as pool:
                ids = list(pool.map(lambda _: store.submit(tenant, 'same', '1', 'a'*64, pdf), range(4)))
            assert len(set(ids)) == 1
            checks.append('concurrent_identical_submission_deduplicated')

            def submit(index):
                try:
                    return store.submit(tenant, 'doc-' + str(index), '1', 'a'*64, pdf)
                except IngestionConflict:
                    return None
            with ThreadPoolExecutor(max_workers=4) as pool:
                additional = list(pool.map(submit, range(5)))
            assert sum(value is not None for value in additional) == 3
            checks.append('concurrent_admission_capped_at_four')
            assert store.claim(tenant + '-other') is None
            checks.append('other_tenant_cannot_claim')
            jobs = [store.claim(tenant) for _ in range(4)]
            assert all(jobs) and store.claim(tenant) is None
            assert len({job['_id'] for job in jobs}) == 4
            checks.append('each_job_has_one_active_claim')
            job = jobs[0]
            result = process_pdf(store.source(job), job['scanned'], Path.cwd(),
                                 VoyageKnowledge(os.environ['VOYAGE_API_KEY'],
                                                 os.environ['VOYAGE_BASE_URL']))
            store.finish(job, result)
            stored = store.db.staged_artifacts.find_one({'_id': job['_id'], 'tenant_id': tenant})
            assert stored['result']['chunks'] == result['chunks']
            checks.append('real_pdf_docling_voyage_durable_staging')
            try:
                store.finish(job, result)
                raise AssertionError('Completed job accepted a second finish')
            except IngestionConflict:
                pass
            checks.append('duplicate_finish_rejected')
            assert store.submit(tenant, job['document_id'], '1', 'a'*64, pdf) == job['_id']
            now[0] += timedelta(seconds=361)
            retried = [store.claim(tenant) for _ in range(3)]
            assert all(item['attempts'] == 2 for item in retried)
            try:
                store.finish(jobs[1], None, failure='worker_failure')
                raise AssertionError('Expired worker accepted')
            except IngestionConflict:
                pass
            checks.append('stale_worker_fenced_after_reclaim')
            now[0] += timedelta(seconds=361)
            assert store.claim(tenant) is None
            assert store.expire_exhausted(tenant) == 3
            assert store.expire_exhausted(tenant) == 0
            assert store.db.staged_artifacts.find_one({'_id': 'quota:' + tenant})['active'] == 0
            checks.append('attempt_budget_exhaustion_releases_quota_once')
        finally:
            # Exact random synthetic tenant only; runtime identity has no delete grant.
            db = operator.telecom_demo_ingestion
            db.jobs.delete_many({'tenant_id': tenant})
            db.staged_artifacts.delete_many({'tenant_id': tenant})
            assert db.jobs.count_documents({'tenant_id': tenant}) == 0
            assert db.staged_artifacts.count_documents({'tenant_id': tenant}) == 0
    evidence = {'checked_at': datetime.now(UTC).isoformat(), 'checks_passed': checks,
                'provider_calls': 1, 'model': 'voyage-context-4', 'dimensions': 1024,
                'published_documents': 0, 'synthetic_probe_cleaned': True,
                'limits': {'active_per_tenant': 4, 'attempts': 2, 'lease_seconds': 360},
                'limitations': ['No curator API or native publication approval enabled',
                                'Ingestion schema validators pending',
                                'Crash recovery may repeat one paid embedding call']}
    Path('compatibility/phase4-ingestion-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Ingestion verification failed: {type(error).__name__}, code={getattr(error, "code", None)}')
        raise SystemExit(1) from None
