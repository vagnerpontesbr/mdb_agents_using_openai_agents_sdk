"""Process one queued demo PDF; does not publish knowledge or resolve Engine review."""

import argparse
import os
from pathlib import Path

from pymongo import MongoClient

from telecom_app.ingestion import IngestionConflict, MongoIngestion
from telecom_app.ingestion_worker import failure_category, process_pdf
from telecom_app.knowledge_voyage import VoyageKnowledge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenant', required=True)
    parser.add_argument('--allow-provider-calls', required=True, action='store_true')
    args = parser.parse_args()
    # One sequential worker, no prewarming; operations have a 15-second budget.
    with MongoClient(os.environ['INGESTION_MONGODB_URI'], timeoutMS=15000,
                     appname='telecom-ingestion-worker') as client:
        store = MongoIngestion(client.telecom_demo_ingestion)
        store.expire_exhausted(args.tenant)
        job = store.claim(args.tenant)
        if job is None:
            print('No available ingestion job')
            return
        try:
            voyage = VoyageKnowledge(os.environ['VOYAGE_API_KEY'], os.environ['VOYAGE_BASE_URL'])
            result = process_pdf(store.source(job), job['scanned'],
                                 Path(__file__).resolve().parents[1], voyage)
            store.finish(job, result)
        except IngestionConflict:
            print('Worker lease or source changed; no result was published')
            raise SystemExit(1) from None
        except Exception as error:
            store.finish(job, None, failure=failure_category(error))
            print('Ingestion failed; sanitized category recorded')
            raise SystemExit(1) from None
        print('PDF staged; native review and publication are still required')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Ingestion worker stopped; details suppressed')
        raise SystemExit(1) from None
