"""Fixed-threshold live cache admission evaluation, with isolated temporary references."""
import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import MongoClient
from compatibility.voyage_http import VoyageHTTPProbe
from telecom_app.knowledge import POLICY, Scope
from telecom_app.knowledge_cache import INDEX, SIMILARITY, MongoCandidateCache, scope_key
from telecom_app.knowledge_search import PROFILE, Candidate


def summary(rows):
    positive = [r for r in rows if r['equivalent']]
    negative = [r for r in rows if not r['equivalent']]
    tp = sum(r['hit'] for r in positive)
    fp = sum(r['hit'] for r in negative)
    return {'comparisons': len(rows), 'equivalent': len(positive), 'different': len(negative),
            'true_hits': tp, 'false_hits': fp, 'missed_equivalents': len(positive)-tp,
            'precision': tp/(tp+fp) if tp+fp else None,
            'equivalent_recall': tp/len(positive) if positive else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-provider-calls', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = Path('examples/telecom/evaluation/semantic-cache-v2.json').read_text()
    dataset = json.loads(raw)
    assert len(dataset['groups']) == 4
    assert all(len(g['cases']) == 12 for g in dataset['groups'])
    tenant = 'semantic-eval-' + uuid4().hex
    scope = Scope(tenant, frozenset({'synthetic-reviewer'}), 'FiberBox', 'demo', '2.x')
    text = 'Synthetic cache admission reference only; not an operational procedure.'
    candidate = Candidate(chunk_id='synthetic', version_key=tenant, revision=1, text=text,
                          text_sha256=hashlib.sha256(text.encode()).hexdigest(), pages=(1,))

    class Reader:
        def chunk(self, tenant_id, version_key, chunk_id, revision):
            return candidate if (tenant_id, version_key, chunk_id, revision) == (
                tenant, tenant, candidate.chunk_id, 1) else None

    probe = VoyageHTTPProbe(os.environ['VOYAGE_API_KEY'], base_url=os.environ['VOYAGE_BASE_URL'])
    with args.output.open('x') as output:
        report = {'started_at': datetime.now(UTC).isoformat(), 'status': 'started',
                  'dataset_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                  'threshold': SIMILARITY, 'embedding_profile': PROFILE,
                  'rows': [], 'scope_checks': [], 'embedding_calls': 0,
                  'cleanup_completed': False, 'cost_usd': None,
                  'limits': [dataset['labels'],
                            'Real MongoDB cache index, scoped identity and production lookup implementation',
                            'Synthetic reference resolver; does not measure final answers or source recall',
                            'Scope overrides are supplied explicitly; query text is not a scope parser',
                            'Held-out partition fixed before calls, but same author and templates',
                            'No threshold tuning; no application source or Engine memory modifications']}
        def save():
            output.seek(0)
            json.dump(report, output, indent=2)
            output.write('\n')
            output.truncate()
            output.flush()
        save()
        with MongoClient(os.environ['KNOWLEDGE_CACHE_URI'], maxPoolSize=1, minPoolSize=0,
                         timeoutMS=15000, appname='telecom-semantic-validation') as client:
            cache = MongoCandidateCache(client.telecom_demo_knowledge, Reader())
            report['index_name'] = INDEX
            save()
            try:
                for group in dataset['groups']:
                    texts = list(dict.fromkeys([group['anchor']] + [c['query'] for c in group['cases']]))
                    vectors = {}
                    for start in range(0, len(texts), 4):
                        batch = texts[start:start+4]
                        report['embedding_calls'] += 1
                        save()
                        result = probe.contextual(batch, documents=False, dimension=1024)
                        for query, row in zip(batch, result['data'], strict=True):
                            vectors[query] = row['data'][0]['embedding']
                    now = datetime.now(UTC)
                    # Reserve a vacant fixed slot with insert, never overwrite another owner's entry.
                    occupied = {row['_id'] for row in cache.collection.find({}, {'_id': 1})}
                    slots = [f'cache-slot-{i}' for i in range(128) if f'cache-slot-{i}' not in occupied]
                    if not slots:
                        raise RuntimeError('No vacant cache slot; refuse to evict application entries')
                    slot = slots[0]
                    cache.collection.insert_one({
                        '_id': slot, 'tenant_id': tenant, 'scope_key': scope_key(scope),
                        'policy_version': POLICY, 'embedding_profile': PROFILE,
                        'query_sha256': hashlib.sha256(group['anchor'].encode()).hexdigest(),
                        'embedding': vectors[group['anchor']], 'created_at': now,
                        'expires_at': now+timedelta(minutes=15),
                        'sources': [{k:getattr(candidate,k) for k in
                                     ('version_key','chunk_id','revision','text_sha256')}]})
                    for _ in range(30):
                        if cache.lookup(scope, group['anchor'], vectors[group['anchor']], datetime.now(UTC)):
                            break
                        time.sleep(2)
                    else:
                        raise TimeoutError('Cache index visibility')
                    for case in group['cases']:
                        hit = cache.lookup(scope, case['query'], vectors[case['query']], datetime.now(UTC))
                        report['rows'].append({'group':group['id'], 'split':group['split'],
                            'case_id':case['id'], 'category':case['category'],
                            'equivalent':case['equivalent'], 'hit':bool(hit)})
                        save()
                    for field, value in [('tenant_id',tenant+'-other'), ('readers',frozenset({'other'})),
                                         ('product','FiberBox X2'), ('firmware_range','1.x'),
                                         ('region','other'), ('language','pt')]:
                        hit = cache.lookup(replace(scope, **{field:value}), group['anchor'],
                                           vectors[group['anchor']], datetime.now(UTC))
                        report['scope_checks'].append({'group':group['id'], 'field':field,
                                                       'denied':hit is None})
                        save()
                    # Delete only our own row. Never delete a slot replaced by another writer.
                    removed = cache.collection.delete_one({'_id':slot, 'tenant_id':tenant})
                    if removed.deleted_count != 1:
                        raise RuntimeError('Evaluation slot overwritten; result requires investigation')
                report['summaries'] = {split:summary([r for r in report['rows'] if r['split']==split])
                                       for split in ('development','held_out')}
                report['overall'] = summary(report['rows'])
                report['scope_denials'] = sum(r['denied'] for r in report['scope_checks'])
                report['status'] = 'completed'
            except Exception as error:
                report['status'] = 'failed'
                report['error_type'] = type(error).__name__
            finally:
                cache.collection.delete_many({'tenant_id':tenant})
                report['cleanup_completed'] = cache.collection.count_documents({'tenant_id':tenant}) == 0
                report['completed_at'] = datetime.now(UTC).isoformat()
                save()
    print(json.dumps({'status':report['status'], 'summary':report.get('overall'),
                      'error_type':report.get('error_type'), 'scope_denials':report.get('scope_denials')}))
    raise SystemExit(0 if report['status']=='completed' else 1)


if __name__ == '__main__':
    main()
