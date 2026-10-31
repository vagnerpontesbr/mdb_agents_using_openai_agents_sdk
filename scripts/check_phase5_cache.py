"""Real cache compatibility without changing published sources or native memory."""

import argparse
import hashlib
import json
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pymongo import MongoClient

from telecom_app.curation import SCOPE
from telecom_app.knowledge_authority import MongoKnowledgeAuthority
from telecom_app.knowledge_cache import MongoCandidateCache, scope_key
from telecom_app.knowledge_mongo import MongoKnowledgeReader
from telecom_app.knowledge_search import retrieve
from telecom_app.knowledge_voyage import VoyageKnowledge


class CountingReader:
    def __init__(self,reader): self.reader,self.searches=reader,0
    def search(self,pipeline):
        self.searches+=1
        return self.reader.search(pipeline)
    def chunk(self,*args): return self.reader.chunk(*args)
    def version(self,*args): return self.reader.version(*args)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    # Reserve the report before any paid request or cache mutation.
    with args.output.open('x') as output:
        output.write('{}\n')
    query='What should I do if the red optical light remains on?'
    with (MongoClient(os.environ['KNOWLEDGE_READER_URI'],maxPoolSize=1,timeoutMS=15000) as reader_client,
          MongoClient(os.environ['KNOWLEDGE_CACHE_URI'],maxPoolSize=1,timeoutMS=15000) as cache_client):
        reader=CountingReader(MongoKnowledgeReader(reader_client.telecom_demo_knowledge))
        authority=MongoKnowledgeAuthority(reader_client.telecom_demo_knowledge)
        cache=MongoCandidateCache(cache_client.telecom_demo_knowledge,reader)
        voyage=VoyageKnowledge(os.environ['VOYAGE_API_KEY'],os.environ['VOYAGE_BASE_URL'])
        vector=voyage.embed_query(query)
        query_hash=hashlib.sha256(query.encode()).hexdigest()
        cleanup={'tenant_id':SCOPE.tenant_id,'scope_key':scope_key(SCOPE),'query_sha256':query_hash}
        # Refuse to overwrite a live entry owned by the interactive application.
        assert cache.collection.find_one(cleanup) is None, 'Use a fresh acceptance environment'
        try:
            first=retrieve(reader,authority,voyage,SCOPE,query,vector,cache=cache)
            assert 'SOP-OPTICAL-DEMO' in first and reader.searches==1
            snapshot=cache.collection.find_one(cleanup)
            assert snapshot and 'sources' in snapshot and 'text' not in snapshot
            import time
            for _ in range(30):
                if cache.lookup(SCOPE,query,vector,datetime.now(UTC)):
                    break
                time.sleep(2)
            else: raise TimeoutError('Cache index visibility deadline')
            second=retrieve(reader,authority,voyage,SCOPE,query,vector,cache=cache)
            assert first==second and reader.searches==1
            assert cache.lookup(replace(SCOPE,tenant_id='different'),query,vector,datetime.now(UTC)) is None
            assert cache.lookup(replace(SCOPE,readers=frozenset({'different'})),query,vector,datetime.now(UTC)) is None
            assert cache.lookup(replace(SCOPE,firmware_range='1.x'),query,vector,datetime.now(UTC)) is None
            cache.collection.update_one(cleanup,{'$set':{'expires_at':datetime.now(UTC)-timedelta(seconds=1)}})
            assert cache.lookup(SCOPE,query,vector,datetime.now(UTC)) is None
            cache.collection.replace_one({'_id':snapshot['_id']},snapshot,upsert=True)
            cache.collection.update_one(cleanup,{'$set':{'sources.0.text_sha256':'f'*64}})
            assert cache.lookup(SCOPE,query,vector,datetime.now(UTC)) is None
            # The retrieval function must discard malformed cached provenance and search again.
            third=retrieve(reader,authority,voyage,SCOPE,query,vector,cache=cache)
            assert third==first and reader.searches==2
            future=datetime.now(UTC)+timedelta(days=60)
            assert 'No currently approved' in retrieve(reader,authority,voyage,SCOPE,query,vector,
                                                       lambda:future,cache=cache)
            evidence={'checked_at':datetime.now(UTC).isoformat(),'actual_query_embeddings':1,
                'actual_rerank_calls':3,'cold_then_warm_exact_answer':True,
                'warm_reused_candidate_set':True,'scope_denials':3,'expired_row_rejected':True,
                'changed_provenance_rejected':True,'corrupt_cache_refreshed_from_search':True,
                'future_source_dates_excluded':True,'published_sources_modified':0,
                'limits':['One synthetic query; no semantic hit-quality claim',
                          'Concurrent source revocation is covered by deterministic tests, not this probe']}
            args.output.write_text(json.dumps(evidence,indent=2)+'\n')
            print(json.dumps(evidence))
        finally:
            cache.collection.delete_many(cleanup)


if __name__=='__main__':
    try: main()
    except Exception as error:
        print(json.dumps({'error_type':type(error).__name__,'details_suppressed':True}))
        raise SystemExit(1) from None
