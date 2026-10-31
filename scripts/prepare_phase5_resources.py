"""Generate the exact Phase 5 Atlas proposal offline. Never applies infrastructure."""

import argparse
import json
from pathlib import Path


def vector_index(database, collection, name, path, dimension, filters):
    return {'database': database, 'collection': collection, 'name': name,
            'type': 'vectorSearch', 'definition': {'fields': [
                {'type': 'vector', 'path': path, 'numDimensions': dimension, 'similarity': 'cosine'},
                *[{'type': 'filter', 'path': field} for field in filters]]}}


def proposal():
    cache_db, eval_db = 'telecom_demo_knowledge', 'telecom_eval_knowledge'
    cache, evaluation = 'retrieval_cache', 'phase5_chunks'
    text = {'bsonType': 'string', 'minLength': 1, 'maxLength': 200}
    date = {'bsonType': 'date'}
    def vector(size):
        return {'bsonType': 'array', 'minItems': size, 'maxItems': size,
                'items': {'bsonType': ['double', 'int', 'long', 'decimal']}}
    def collection(database, name, fields):
        return {'database': database, 'name': name, 'validationLevel': 'strict',
                'validationAction': 'error', 'validator': {'$jsonSchema': {
                    'bsonType': 'object', 'required': list(fields),
                    'additionalProperties': False, 'properties': fields}}}
    cache_fields = dict(_id=text, tenant_id=text, scope_key=text, policy_version=text,
        embedding_profile=text, query_sha256=text, embedding=vector(1024),
        created_at=date, expires_at=date,
        sources={'bsonType': 'array', 'minItems': 1, 'maxItems': 20, 'items': {
            'bsonType': 'object', 'required': ['version_key', 'chunk_id', 'revision', 'text_sha256'],
            'additionalProperties': False, 'properties': {
                'version_key': text, 'chunk_id': text, 'revision': {'bsonType': 'int', 'minimum': 1},
                'text_sha256': text}}})
    eval_fields = dict(_id=text, dataset_id=text, tenant_id=text, version_key=text,
        chunk_id=text, source_checksum=text, embedding_profile=text, eligible={'bsonType':'bool'},
        text={'bsonType':'string','minLength':1,'maxLength':20000},
        embedding_256=vector(256), embedding_1024=vector(1024))
    lexical = {'database': eval_db, 'collection': evaluation, 'name': 'phase5_lexical_v1',
        'type': 'search', 'definition': {'analyzer': 'lucene.standard', 'mappings': {
            'dynamic': False, 'fields': {'text': {'type': 'string'},
                'dataset_id': {'type':'token'}, 'tenant_id': {'type':'token'},
                'eligible': {'type':'boolean'}}}}}
    return {
        'status': 'proposed_not_applied', 'cluster': 'OpenAI-SDK',
        'project_id': '67b385a7976edf15ecc62e06',
        'collections': [collection(cache_db, cache, cache_fields),
                        collection(eval_db, evaluation, eval_fields)],
        'search_indexes': [
            vector_index(cache_db, cache, 'retrieval_cache_context_1024_v1', 'embedding', 1024,
                         ['tenant_id','scope_key','policy_version','embedding_profile','expires_at']),
            lexical,
            *[vector_index(eval_db, evaluation, f'phase5_context_{size}_v1',
                           f'embedding_{size}', size, ['dataset_id','tenant_id','eligible'])
              for size in (256,1024)]],
        'classic_indexes': [
            {'database':cache_db,'collection':cache,'name':'cache_expiry',
             'key':{'expires_at':1},'expireAfterSeconds':0},
            {'database':cache_db,'collection':cache,'name':'cache_scope_created',
             'key':{'tenant_id':1,'scope_key':1,'created_at':1}},
            {'database':eval_db,'collection':evaluation,'name':'evaluation_chunk_identity',
             'key':{'dataset_id':1,'version_key':1,'chunk_id':1},'unique':True}],
        'runtime_identities': [
            {'username':'telecom_knowledge_cache','role':'telecom_knowledge_cache_rw',
             'scope':{'type':'CLUSTER','name':'OpenAI-SDK'},
             'privileges':[{'database':cache_db,'collection':cache,
                            'actions':['FIND','INSERT','UPDATE','REMOVE']}]},
            {'username':'telecom_phase5_evaluator','role':'telecom_phase5_evaluator_rw',
             'scope':{'type':'CLUSTER','name':'OpenAI-SDK'},
             'privileges':[{'database':eval_db,'collection':evaluation,
                            'actions':['FIND','INSERT','UPDATE','REMOVE']}]}],
        'bounded_data_changes': {
            'existing_documents_modified':0, 'maximum_evaluation_chunks':200,
            'maximum_demo_cache_entries':128, 'cache_max_age_seconds':900,
            'cleanup':'Only new evaluation/cache records; never Phase 0 or Engine records'},
        'runtime_configuration': {
            'private_local_credentials':['KNOWLEDGE_CACHE_URI','EVALUATION_MONGODB_URI'],
            'workspace_secret_additions':['KNOWLEDGE_CACHE_URI'],
            'shared_policy_changes':[], 'new_tool_names':[],
            'hosted_deployment':'Only after local and domain acceptance; current tool names retained'},
        'acceptance_requirements': [
            'Fresh role/index/validator drift check before application',
            'Cache holds candidate source references, not conversation memory or authoritative answers',
            'Revalidate tenant/ACL/source versions/checksums/dates before any cached result is used',
            'Similarity never grants authorization; cache misses/errors retain governed retrieval',
            'Expiry enforced on reads; TTL is asynchronous physical cleanup only',
            'Compare actual 256/1024 provider output; no unsupported vector slicing',
            'Negative control confined to evaluation identity and collection',
            'No new grants to current application or Engine memory identities'],
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with args.output.open('x') as output:
        json.dump(proposal(),output,indent=2)
        output.write('\n')
    print('Created proposal only; no Atlas or Engine writes.')


if __name__ == '__main__':
    main()
