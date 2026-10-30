"""Opt-in PDF-page to contextual-embedding/rerank acceptance; no database writes."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from telecom_app.knowledge import canonical
from telecom_app.knowledge_voyage import VoyageKnowledge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pages', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-live', action='store_true')
    args = parser.parse_args()
    if not args.allow_live:
        parser.error('Explicit --allow-live is required for paid Voyage requests')
    client = VoyageKnowledge(os.environ.get('VOYAGE_API_KEY', ''),
                             os.environ.get('VOYAGE_BASE_URL', 'https://ai.mongodb.com/v1'))
    report = {'at': datetime.now(timezone.utc).isoformat(), 'checks': [],
              'scope': 'synthetic PDF extraction and provider contract; no retrieval quality claim'}
    for path in args.pages:
        data = json.loads(path.read_text())
        if data.get('contract') != 'telecom-pdf-pages-v1':
            raise ValueError('Unsupported page contract')
        pages = data['pages']
        expected = ['Check the optical cable before restarting the router.',
                    'Open a support ticket if the red light remains on.']
        if len(pages) != 2 or not all(text in canonical(page)
                                      for text, page in zip(expected, pages, strict=True)):
            raise ValueError('Expected synthetic fixture text on its exact page')
        chunks = client.embed_pages(pages)
        query = 'What should I check before restarting the router?'
        embedding = client.embed_query(query)
        ranked = client.rank(query, [chunk.source.text for chunk in chunks])
        report['checks'].append({'fixture': path.name, 'checksum': data['checksum'],
            'pages': len(pages), 'ocr': data['ocr'], 'chunks': len(chunks),
            'aligned_pages': [list(c.source.pages) for c in chunks],
            'all_pages_known': all(c.source.page_known for c in chunks),
            'dimension': len(embedding), 'reranked_indices': ranked})
    report['status'] = 'passed'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Provider acceptance failed: {type(error).__name__}; details suppressed')
        raise SystemExit(1) from None
