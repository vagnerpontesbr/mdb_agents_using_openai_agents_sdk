"""Real native Engine review and MongoDB publication for a retained synthetic demo PDF.

Runs with an operator-admitted initial demo-owner identity. Browser authentication
has separate tests; this script does not claim to test login or session cookies.
"""

import base64
import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from pymongo import MongoClient

from telecom_app.curation import OWNER, SCOPE, TENANT, Upload
from telecom_app.curation_runtime import configure
from telecom_app.ingestion_worker import process_pdf
from telecom_app.knowledge import Scope
from telecom_app.knowledge_search import retrieve


def main():
    with MongoClient(os.environ['KNOWLEDGE_READER_URI'], timeoutMS=15000) as client:
        owner = client.telecom_demo_knowledge.owners.find_one({'tenant_id': TENANT, 'owner_id': OWNER})
    actor = SimpleNamespace(user_id=owner['user_ids'][0], role='admin')
    identity = SimpleNamespace(principal=lambda token: actor)
    service, clients = configure(identity)
    stage = 'upload'
    execution_ids = []
    try:
        now = datetime.now(UTC)
        data = Upload(pdf_base64=base64.b64encode(Path('artifacts/compatibility/pdf/text.pdf').read_bytes()).decode(),
            document_id='SOP-OPTICAL-DEMO', version_id=now.strftime('%Y%m%dT%H%M%S'),
            title='Synthetic optical cable procedure', created_at=now-timedelta(days=30),
            effective_from=now-timedelta(days=1), last_reviewed_at=now-timedelta(hours=1),
            expires_at=now+timedelta(days=30), review_due_at=now+timedelta(days=7))
        uploaded = service.upload('operator-admitted-probe', data)
        job_id = uploaded['job_id']
        assert service.upload('operator-admitted-probe', data)['job_id'] == job_id
        stage = 'processing'
        job = service.ingestion.claim(TENANT, job_id)
        assert job is not None
        result = process_pdf(service.ingestion.source(job), False, Path.cwd(), service.voyage)
        service.ingestion.finish(job, result)

        def wait(execution, desired):
            for _ in range(60):
                status = service.review.present('operator-admitted-probe', execution)
                if status['status'] == desired:
                    return status
                if status['status'] in ('error', 'cancelled'):
                    raise RuntimeError('Native execution failed')
                time.sleep(2)
            raise TimeoutError('Native execution did not reach the required state')

        for decision in ('reject', 'approve'):
            stage = 'native_' + decision + '_request'
            pending = service.start_review('operator-admitted-probe', job_id)
            execution = pending['execution_id']
            execution_ids.append(execution)
            pending = wait(execution, 'suspended')
            stage = 'native_' + decision + '_resume'
            service.decide('operator-admitted-probe', execution, pending['action_digest'], decision)
            final = wait(execution, 'completed')
            assert final['result']['status'] == ('rejected' if decision == 'reject' else 'approved')
            if decision == 'reject':
                try:
                    service.publish('operator-admitted-probe', execution)
                    raise AssertionError('Rejected review permitted publication')
                except Exception as error:
                    if isinstance(error, AssertionError):
                        raise
        stage = 'publish'
        published = service.publish('operator-admitted-probe', execution_ids[-1])
        assert service.publish('operator-admitted-probe', execution_ids[-1]) == published
        stage = 'search_visibility'
        vector = service.voyage.embed_query('What should I do if the red optical light remains on?')
        answer = ''
        for _ in range(30):
            answer = retrieve(service.reader, service.publisher, service.voyage, SCOPE,
                              'red optical light', vector)
            if 'SOP-OPTICAL-DEMO' in answer:
                break
            time.sleep(2)
        assert 'SOP-OPTICAL-DEMO' in answer and 'pages 1, 2' in answer
        assert 'Open a support ticket if the red light remains on.' in answer
        for denied in (Scope('different-tenant', SCOPE.readers, SCOPE.product, SCOPE.region, SCOPE.firmware_range),
                       Scope(TENANT, frozenset({'different-reader'}), SCOPE.product, SCOPE.region, SCOPE.firmware_range)):
            assert 'No currently approved' in retrieve(service.reader, service.publisher, service.voyage,
                                                       denied, 'optical', vector)
        assert service.source('operator-admitted-probe', published['version_key']) == service.ingestion.source(job)
        evidence = {'checked_at': datetime.now(UTC).isoformat(), 'document_id': data.document_id,
                    'version_key': published['version_key'], 'job_id': job_id,
                    'native_executions': execution_ids, 'native_reject_denied_publication': True,
                    'native_approve_published': True, 'publication_idempotent': True,
                    'native_hybrid_cited_answer': True, 'tenant_acl_denials': True,
                    'original_source_verified': True, 'synthetic_document_retained': True,
                    'limitations': ['Operator-admitted identity, not a browser login test',
                                    'Hosted technical specialist integration remains pending']}
        Path('compatibility/phase4-publication-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
        print(json.dumps(evidence))
    except Exception as error:
        print(json.dumps({'stage': stage, 'error_type': type(error).__name__,
                          'execution_ids': execution_ids, 'details_suppressed': True}))
        raise SystemExit(1) from None
    finally:
        for client in clients:
            client.close()


if __name__ == '__main__':
    main()
