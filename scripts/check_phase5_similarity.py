"""Bounded contextual cache-threshold screen; not end-to-end cache quality."""
import argparse
import json
import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compatibility.voyage_http import VoyageHTTPProbe
from telecom_app.knowledge_cache import SIMILARITY

QUERIES = [
    ('anchor', 'How should I resolve E17 on FiberBox X1 firmware 2.x?', True),
    ('exact', 'How should I resolve E17 on FiberBox X1 firmware 2.x?', True),
    ('paraphrase', 'What steps resolve error E17 on my FiberBox X1 running firmware 2.x?', True),
    ('different-firmware', 'How should I resolve E17 on FiberBox X1 firmware 1.x?', False),
    ('different-alarm', 'How should I resolve E18 on FiberBox X1 firmware 2.x?', False),
    ('different-product', 'How should I resolve E17 on FiberBox X2 firmware 2.x?', False),
    ('invoice', 'How can I dispute a charge on my telecom invoice?', False),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-provider-calls', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.output.open('x') as output:
        report = {'checked_at': datetime.now(UTC).isoformat(), 'threshold': SIMILARITY,
                  'status': 'started', 'rows': [], 'cost_usd': None,
                  'limits': ['Seven developer-authored synthetic queries, not external SME validation',
                             'Cosine score screen only; does not measure source recall or final answers',
                             'Changed equipment must also be rejected by authoritative applicability',
                             'No threshold tuning on this small sample; no production quality guarantee']}
        def save():
            output.seek(0)
            json.dump(report, output, indent=2)
            output.write('\n')
            output.truncate()
            output.flush()
        save()
        probe = VoyageHTTPProbe(os.environ['VOYAGE_API_KEY'], base_url=os.environ['VOYAGE_BASE_URL'])
        vectors = []
        for start in (0, 4):
            result = probe.contextual([q[1] for q in QUERIES[start:start+4]],
                                      documents=False, dimension=1024)
            vectors.extend(row['data'][0]['embedding'] for row in result['data'])
        anchor = vectors[0]
        for (case, _, expected), vector in zip(QUERIES[1:], vectors[1:], strict=True):
            cosine = sum(a*b for a,b in zip(anchor,vector,strict=True)) / (
                math.sqrt(sum(a*a for a in anchor))*math.sqrt(sum(b*b for b in vector)))
            score = (1+cosine)/2
            report['rows'].append({'case_id': case, 'equivalent_label': expected,
                                   'score': score, 'admitted_by_threshold': score >= SIMILARITY})
        report['false_hits'] = sum(r['admitted_by_threshold'] and not r['equivalent_label'] for r in report['rows'])
        report['missed_equivalents'] = sum(not r['admitted_by_threshold'] and r['equivalent_label'] for r in report['rows'])
        report['status'] = 'completed'
        save()
        print(json.dumps({'false_hits':report['false_hits'], 'missed_equivalents':report['missed_equivalents']}))


if __name__ == '__main__':
    main()
