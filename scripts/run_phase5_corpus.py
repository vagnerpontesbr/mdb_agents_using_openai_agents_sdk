"""Isolated PDF/contextual-dimension experiment; never publishes demo knowledge.

Labels and business rules are synthetic developer-authored controls, not independent
human validation. The negative-control switch exists only in this offline script.
"""

import argparse
import hashlib
import json
import os
import time
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compatibility.voyage_http import VoyageHTTPProbe
from telecom_app.evaluation import ranking_metrics
from telecom_app.knowledge import canonical, align_chunks

QUESTIONS=[
    ('alarm','How should I resolve E17 on my FiberBox X1 firmware 2.x?','current'),
    ('incident','Does E17 on firmware 2.x require checking a provisioning incident?','current'),
    ('reset','Should I reset the legacy provisioning profile on firmware 2.x?','current'),
    ('unknown','What should support do when product or firmware details are unknown?','current'),
    ('wifi','Where should I place my Wi-Fi router for better indoor coverage?','wifi'),
    ('invoice','How can I dispute a line item on my invoice?','invoice'),
]


def pipeline(dataset, query, vector, dimension, governed=True):
    filters={'dataset_id':dataset,'tenant_id':'synthetic-evaluation'}
    if governed: filters['eligible']=True
    lexical=[{'equals':{'path':key,'value':value}} for key,value in filters.items()]
    return [{'$rankFusion':{'input':{'pipelines':{
        'lexical':[{'$search':{'index':'phase5_lexical_v1','compound':{
            'must':[{'text':{'path':'text','query':query}}],'filter':lexical}}},{'$limit':10}],
        'semantic':[{'$vectorSearch':{'index':f'phase5_context_{dimension}_v1',
            'path':f'embedding_{dimension}','queryVector':vector,'exact':True,'limit':10,
            'filter':filters}}]}},'combination':{'weights':{'lexical':.5,'semantic':.5}}}},
        {'$limit':10},{'$project':{'_id':0,'version_key':1,'chunk_id':1,'text':1,'eligible':1}}]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-provider-calls',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with args.output.open('x') as output:
        report={'started_at':datetime.now(UTC).isoformat(),'status':'started',
                'provider_calls':{'contextual_documents':0,'contextual_queries':0,'rerank':0},
                'rows':[],'labels':'developer-authored synthetic references; not SME-approved',
                'cost_usd':None,'sources':{},'cleanup_completed':False}
        def save():
            output.seek(0);json.dump(report,output,indent=2);output.write('\n');output.truncate();output.flush()
        save()
        names=['legacy','current','wifi','invoice']
        pages=[json.loads(Path(f'artifacts/phase5/pdf/{name}.json').read_text()) for name in names]
        texts=[' '.join(canonical(page) for page in data['pages']) for data in pages]
        probe=VoyageHTTPProbe(os.environ['VOYAGE_API_KEY'],base_url=os.environ['VOYAGE_BASE_URL'])
        dataset='phase5-'+uuid4().hex
        with MongoClient(os.environ['EVALUATION_MONGODB_URI'],maxPoolSize=1,minPoolSize=0,
                         timeoutMS=15000,appname='telecom-phase5-corpus') as client:
            collection=client.telecom_eval_knowledge.phase5_chunks
            try:
                document_vectors={}
                for dimension in (256,1024):
                    report['provider_calls']['contextual_documents']+=1;save()
                    document_vectors[dimension]=probe.contextual(texts,documents=True,dimension=dimension)
                records=[]
                for i,name in enumerate(names):
                    short=document_vectors[256]['data'][i]['data']
                    full=document_vectors[1024]['data'][i]['data']
                    assert [c['text'] for c in short]==[c['text'] for c in full]
                    chunks=align_chunks(pages[i]['pages'],[c['text'] for c in full])
                    assert all(c.pages==(1,) for c in chunks)
                    report['sources'][name]={'checksum':pages[i]['checksum'],'pages':1,
                        'chunks':len(chunks),'parser':pages[i]['parser_version']}
                    for index,(a,b) in enumerate(zip(short,full,strict=True)):
                        row=dict(_id=f'{dataset}:{name}:{index}',dataset_id=dataset,
                            tenant_id='synthetic-evaluation',version_key=name,chunk_id=str(index),
                            source_checksum=pages[i]['checksum'],
                            embedding_profile='voyage-context-4:comparison-v1',eligible=name!='legacy',
                            text=b['text'],embedding_256=a['embedding'],embedding_1024=b['embedding'])
                        records.append(row)
                        if name=='legacy':
                            for variant in ('negative','missing'):
                                records.append({**row,'_id':row['_id']+':'+variant,
                                                'dataset_id':dataset+':'+variant})
                assert len(records)<=200
                collection.insert_many(records)
                report['inserted_chunks']=len(records)
                query_vectors={}
                for dimension in (256,1024):
                    vectors=[]
                    for start in (0,4):
                        report['provider_calls']['contextual_queries']+=1;save()
                        response=probe.contextual([q[1] for q in QUESTIONS[start:start+4]],
                                                  documents=False,dimension=dimension)
                        vectors.extend(item['data'][0]['embedding'] for item in response['data'])
                    query_vectors[dimension]=vectors
                # Await only visibility, not a desired rank; no repeated provider request.
                for _ in range(30):
                    observed=list(collection.aggregate(pipeline(dataset,QUESTIONS[0][1],
                        query_vectors[1024][0],1024)))
                    if len({row['version_key'] for row in observed})==3: break
                    time.sleep(2)
                else: raise TimeoutError('Evaluation corpus index visibility')
                for dimension in (256,1024):
                    for i,(case_id,query,expected) in enumerate(QUESTIONS):
                        started=time.monotonic()
                        candidates=list(collection.aggregate(pipeline(dataset,query,
                                                        query_vectors[dimension][i],dimension)))
                        assert candidates and all(row['eligible'] for row in candidates)
                        report['provider_calls']['rerank']+=1;save()
                        ranked=probe.rerank(query,[row['text'] for row in candidates],top_k=min(3,len(candidates)))
                        order=[candidates[row['index']]['version_key'] for row in ranked['data']]
                        unique=list(dict.fromkeys(order))
                        report['rows'].append({'case_id':case_id,'dimension':dimension,
                            'ranked_versions':unique,'metrics_at_1':ranking_metrics(unique,{expected},1),
                            'metrics_at_3':ranking_metrics(unique,{expected},3),
                            'elapsed_seconds':round(time.monotonic()-started,3),
                            'stale_source_exposed': 'legacy' in unique})
                        save()
                negative=list(collection.aggregate(pipeline(dataset+':negative',QUESTIONS[0][1],
                                                query_vectors[1024][0],1024,governed=False)))
                missing=list(collection.aggregate(pipeline(dataset+':missing',QUESTIONS[0][1],
                                                query_vectors[1024][0],1024,governed=True)))
                assert negative and all(row['version_key']=='legacy' for row in negative) and not missing
                report['stale_control']={
                    'actual_retrieved_versions':list(dict.fromkeys(row['version_key'] for row in negative)),
                    'retrieval_against_stale_gold':ranking_metrics(['legacy'],{'legacy'},1),
                    'retrieval_against_current_gold':ranking_metrics(['legacy'],{'current'},1),
                    'governed_without_replacement_abstains':not missing,
                    'llm_answer_generated':False,'faithfulness':None,'current_business_correctness':None}
                report['vector_payload_bytes_float32']={'256':256*4,'1024':1024*4}
                report['status']='completed'
                report['limitations']=['Four synthetic PDFs and six queries; no corpus generalization',
                    'Eligibility flags are experiment labels, not native publication approval',
                    'No production source, governance state, cache or memory was changed',
                    'Vector payload sizes exclude BSON/index overhead; latency is not a capacity benchmark',
                    'No generated answer or calibrated judge in this experiment']
            except Exception as error:
                report.update(status='failed',error_type=type(error).__name__)
                raise
            finally:
                collection.delete_many({'dataset_id':{'$in':[dataset,dataset+':negative',dataset+':missing']}})
                report['cleanup_completed']=True
                report['completed_at']=datetime.now(UTC).isoformat();save()
        print(json.dumps({'status':report['status'],'rows':len(report['rows']),
                          'provider_calls':report['provider_calls'],'cleanup_completed':True}))


if __name__=='__main__':
    try: main()
    except Exception as error:
        print(json.dumps({'error_type':type(error).__name__,'details_suppressed':True}))
        raise SystemExit(1) from None
