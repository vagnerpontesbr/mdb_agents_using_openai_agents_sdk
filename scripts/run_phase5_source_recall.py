"""Bounded actual warm-cache versus fresh hybrid candidate recall over synthetic sources."""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import MongoClient
from compatibility.voyage_http import VoyageHTTPProbe
from scripts.run_phase5_corpus import pipeline
from scripts.phase5_calibration import select, evaluate
import telecom_app.knowledge_cache as cache_module
from telecom_app.evaluation import ranking_metrics
from telecom_app.knowledge import POLICY, Scope
from telecom_app.knowledge_cache import MongoCandidateCache, SIMILARITY, scope_key
from telecom_app.knowledge_search import Candidate, PROFILE
from telecom_app.knowledge_voyage import VoyageKnowledge


def source_metrics(candidates, ranked, relevant):
    ids = [c.version_key for c in candidates]
    ordered = [candidates[i].version_key for i in ranked]
    return {'candidate_recall': len(set(ids)&set(relevant))/len(relevant),
            'candidate_ids':ids, 'ranked_ids':ordered,
            'top1':ranking_metrics(ordered,set(relevant),1),
            'top3':ranking_metrics(ordered,set(relevant),3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-provider-calls', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dataset', type=Path, default=Path('examples/telecom/evaluation/cache-source-recall-v1.json'))
    parser.add_argument('--calibrate', action='store_true')
    args = parser.parse_args()
    raw = args.dataset.read_text()
    data = json.loads(raw)
    v3=data['version']=='cache-source-calibration-v3'
    assert len(data['sources']) == (40 if v3 else 32)
    assert sum(len(g['cases']) for g in data['groups']) == (34 if v3 else (16 if args.calibrate else 12))
    if args.calibrate:
        assert data['version'] in ('cache-source-calibration-v2','cache-source-calibration-v3')
        assert [g['id'] for g in data['groups']]==(['development-0','development-1','held_out-0','held_out-1'] if v3 else ['development','held_out'])
    run = 'source-recall-'+uuid4().hex
    scope = Scope(run, frozenset({'synthetic-reviewer'}), 'demo-family', 'demo', '2.x')
    probe = VoyageHTTPProbe(os.environ['VOYAGE_API_KEY'],base_url=os.environ['VOYAGE_BASE_URL'])
    reranker = VoyageKnowledge(os.environ['VOYAGE_API_KEY'],os.environ['VOYAGE_BASE_URL'])
    with args.output.open('x') as output:
        report = {'started_at':datetime.now(UTC).isoformat(),'status':'started',
                  'dataset_sha256':hashlib.sha256(raw.encode()).hexdigest(),'threshold':SIMILARITY,
                  'rows':[],'calls':{'document_embeddings':0,'query_embeddings':0,'reranks':0},
                  'cleanup_completed':False,'cost_usd':None,
                  'limits':[data['labels'],
                            'Actual isolated corpus hybrid retrieval, cache lookup and provider reranking',
                            'Exact vector baseline with 20 candidates; not production ANN recall',
                            'Synthetic applicability labels, not native publication or final answer proof',
                            'Same trusted broad demo scope for text-only equipment changes',
                            'Partitions fixed before calls; optional selection uses development only; no judge calls']}
        def save():
            output.seek(0);json.dump(report,output,indent=2);output.write('\n');output.truncate();output.flush()
        save()
        with (MongoClient(os.environ['EVALUATION_MONGODB_URI'],maxPoolSize=1,timeoutMS=15000) as ec,
              MongoClient(os.environ['KNOWLEDGE_CACHE_URI'],maxPoolSize=1,timeoutMS=15000) as cc):
            collection = ec.telecom_eval_knowledge.phase5_chunks
            def candidate(row):
                return Candidate(chunk_id=row['chunk_id'],version_key=row['version_key'],revision=1,
                                 text=row['text'],text_sha256=hashlib.sha256(row['text'].encode()).hexdigest(),pages=(1,))
            class Reader:
                def chunk(self,tenant,key,chunk,revision):
                    if tenant!=run or revision!=1: return None
                    row=collection.find_one({'dataset_id':run,'version_key':key,'chunk_id':chunk})
                    return candidate(row) if row else None
            cache=MongoCandidateCache(cc.telecom_demo_knowledge,Reader())
            def search(query,vector):
                stages=pipeline(run,query,vector,1024)
                for branch in stages[0]['$rankFusion']['input']['pipelines'].values():
                    for stage in branch:
                        if '$limit' in stage: stage['$limit']=20
                        if '$vectorSearch' in stage: stage['$vectorSearch']['limit']=20
                stages[1]['$limit']=20
                return [candidate(row) for row in collection.aggregate(stages)]
            def rank(query,candidates):
                report['calls']['reranks']+=1;save()
                return reranker.rank(query,[c.text for c in candidates])
            try:
                docs=data['sources'];vectors={256:[],1024:[]}
                for dim in vectors:
                    for start in range(0,len(docs),4):
                        report['calls']['document_embeddings']+=1;save()
                        result=probe.contextual([d['text'] for d in docs[start:start+4]],documents=True,dimension=dim)
                        for row in result['data']:
                            assert len(row['data'])==1,'Fixture unexpectedly split into multiple chunks'
                            vectors[dim].append(row['data'][0])
                rows=[]
                for i,doc in enumerate(docs):
                    assert vectors[256][i]['text']==vectors[1024][i]['text']
                    text=vectors[1024][i]['text']
                    rows.append({'_id':run+':'+doc['id'],'dataset_id':run,'tenant_id':'synthetic-evaluation',
                        'version_key':doc['id'],'chunk_id':'0','source_checksum':hashlib.sha256(doc['text'].encode()).hexdigest(),
                        'embedding_profile':PROFILE,'eligible':True,'text':text,
                        'embedding_256':vectors[256][i]['embedding'],'embedding_1024':vectors[1024][i]['embedding']})
                collection.insert_many(rows)
                queries=list(dict.fromkeys(c['query'] for g in data['groups'] for c in g['cases']))
                qv={}
                for start in range(0,len(queries),4):
                    batch=queries[start:start+4];report['calls']['query_embeddings']+=1;save()
                    response=probe.contextual(batch,documents=False,dimension=1024)
                    for q,row in zip(batch,response['data'],strict=True):qv[q]=row['data'][0]['embedding']
                # Readiness checks all rows in each index, not a desired relevance ranking.
                for _ in range(30):
                    observed=list(collection.aggregate([{'$vectorSearch':{'index':'phase5_context_1024_v1',
                        'path':'embedding_1024','queryVector':qv[queries[0]],'exact':True,'limit':40,
                        'filter':{'dataset_id':run}}},{'$project':{'_id':1}}]))
                    lexical=list(collection.aggregate([{'$search':{'index':'phase5_lexical_v1',
                        'equals':{'path':'dataset_id','value':run}}},{'$count':'n'}]))
                    if len(observed)==len(docs) and lexical and lexical[0]['n']==len(docs):break
                    time.sleep(2)
                else:raise TimeoutError('Corpus index visibility')
                if args.calibrate:
                    report['calibration_policy']=data['calibration_policy'];save()
                selected_threshold=SIMILARITY
                for group in data['groups']:
                    if args.calibrate and group['id'].startswith('held_out'):
                        chosen=report['calibration']['selected']
                        if chosen is None:
                            report['validation_not_attempted']='No development threshold met the frozen policy'
                            break
                        selected_threshold=chosen
                        report['selection_frozen_before_validation']=True;save()
                    anchor=group['anchor'];seed=search(anchor,qv[anchor]);assert len(seed)==20
                    occupied={r['_id'] for r in cache.collection.find({}, {'_id':1})}
                    free=[f'cache-slot-{i}' for i in range(128) if f'cache-slot-{i}' not in occupied]
                    assert free,'No vacant cache slot'
                    slot=free[0];now=datetime.now(UTC)
                    cache.collection.insert_one({'_id':slot,'tenant_id':run,'scope_key':scope_key(scope),
                        'policy_version':POLICY,'embedding_profile':PROFILE,
                        'query_sha256':hashlib.sha256(anchor.encode()).hexdigest(),'embedding':qv[anchor],
                        'created_at':now,'expires_at':now+timedelta(minutes=15),
                        'sources':[{k:getattr(c,k) for k in ('version_key','chunk_id','revision','text_sha256')} for c in seed]})
                    for _ in range(30):
                        if cache.lookup(scope,anchor,qv[anchor],datetime.now(UTC)):break
                        time.sleep(2)
                    else:raise TimeoutError('Cache index visibility')
                    for case in group['cases']:
                        query=case['query'];fresh=search(query,qv[query])
                        previous_threshold=cache_module.SIMILARITY
                        try:
                            # This process only; no deployed/global configuration is written.
                            cache_module.SIMILARITY=selected_threshold
                            hit=cache.lookup(scope,query,qv[query],datetime.now(UTC))
                        finally:
                            cache_module.SIMILARITY=previous_threshold
                        baseline=source_metrics(fresh,rank(query,fresh),case['relevant_sources'])
                        counterfactual=source_metrics(seed,rank(query,seed),case['relevant_sources']) if args.calibrate else None
                        warm=counterfactual if hit and args.calibrate else (
                            source_metrics(hit,rank(query,hit),case['relevant_sources']) if hit else None)
                        extra={}
                        if args.calibrate:
                            scores=list(cache.collection.aggregate([
                                {'$vectorSearch':{'index':cache_module.INDEX,'path':'embedding',
                                    'queryVector':qv[query],'exact':True,'limit':1,
                                    'filter':{'tenant_id':run,'scope_key':scope_key(scope)}}},
                                {'$project':{'_id':1,'score':{'$meta':'vectorSearchScore'}}}]))
                            assert len(scores)==1 and scores[0]['_id']==slot
                            extra={'similarity':scores[0]['score'],'counterfactual_warm':counterfactual,
                                   'threshold_used':selected_threshold}
                        report['rows'].append({**extra,'partition':group['id'],'case_id':case['id'],'cache_hit':bool(hit),
                            'expected_sources':case['relevant_sources'],'fresh':baseline,'warm':warm,
                            'effective':warm if hit else baseline,
                            'recall_lost_on_hit':bool(warm and warm['candidate_recall']<baseline['candidate_recall'])})
                        save();print(json.dumps({'partition':group['id'],'case':case['id'],'cache_hit':bool(hit)}),flush=True)
                    if args.calibrate and group['id'].startswith('development'):
                        report['calibration']=select(report['rows'],data['calibration_policy']['thresholds'],
                            data['calibration_policy']['minimum_paraphrase_hit_rate'],
                            per_group=data['calibration_policy'].get('minimum_per_group',False));save()
                    elif args.calibrate:
                        report['validation']=evaluate([r for r in report['rows'] if r['partition'].startswith('held_out')],selected_threshold)
                        report['validation_baseline']=evaluate([r for r in report['rows'] if r['partition'].startswith('held_out')],SIMILARITY)
                        save()
                    assert cache.collection.delete_one({'_id':slot,'tenant_id':run}).deleted_count==1
                report['summary']={'cases':len(report['rows']),'cache_hits':sum(r['cache_hit'] for r in report['rows']),
                    'hits_losing_candidate_recall':sum(r['recall_lost_on_hit'] for r in report['rows']),
                    'fresh_top1_correct':sum(r['fresh']['top1']['precision']==1 for r in report['rows']),
                    'effective_top1_correct':sum(r['effective']['top1']['precision']==1 for r in report['rows'])}
                report['status']='completed'
            except Exception as error:
                report.update(status='failed',error_type=type(error).__name__)
            finally:
                collection.delete_many({'dataset_id':run});cache.collection.delete_many({'tenant_id':run})
                report['cleanup_completed']=collection.count_documents({'dataset_id':run})==0 and cache.collection.count_documents({'tenant_id':run})==0
                report['completed_at']=datetime.now(UTC).isoformat();save()
    print(json.dumps({'status':report['status'],'summary':report.get('summary'),'error_type':report.get('error_type')}))
    raise SystemExit(0 if report['status']=='completed' else 1)


if __name__=='__main__':main()
