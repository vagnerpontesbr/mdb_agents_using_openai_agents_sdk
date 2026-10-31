"""Bounded, opt-in live Engine evaluation; no business writes or automatic retries.

Each case uses a new session for the existing synthetic document owner. Engine
memory remains enabled: this measures deployed behavior, not a reset-memory trial.
"""

import argparse
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from pymongo import MongoClient

from telecom_app.evaluation import EvaluationDataset, fingerprint, measure, summarize
from telecom_app.journey import EngineAPI, JourneyService, session_id
from compatibility.demo_auth.engine import WORKSPACE


def release_completed_runtime(engine, session, execution):
    """Release only this run's terminal runtime; preserve durable Engine history."""
    state = engine.execution(execution)
    if state.get('session_id') != session or state.get('status') != 'completed':
        raise ValueError('Only the verified completed evaluation session may be released')
    path = f'workspaces/{WORKSPACE}/runtime-sessions'
    def reserved():
        rows = engine.call(path).get('sessions')
        if not isinstance(rows, list) or len(rows) > 300:
            raise ValueError('Unbounded runtime session response')
        return any(row.get('session_id') == session for row in rows)
    if not reserved():
        return 'already_released'
    engine.call(f'{path}/{session}/stop', {})
    for _ in range(20):
        time.sleep(2)
        if not reserved():
            return 'released'
    raise TimeoutError('Native runtime release not confirmed; stop the evaluation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live', action='store_true')
    parser.add_argument('--repeats', type=int, choices=range(2, 4), default=3)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pause-seconds', type=int, choices=(0, 5, 15, 30), default=5)
    args = parser.parse_args()
    path = Path('examples/telecom/evaluation/journey-v1.json')
    raw = path.read_text()
    dataset = EvaluationDataset.model_validate_json(raw)
    if len(dataset.cases) * args.repeats > 12:
        parser.error("The live evaluation budget is at most twelve invocations")
    if not args.allow_live:
        print(json.dumps({'live_calls': 0, 'planned_invocations': len(dataset.cases)*args.repeats,
                          'requires': '--allow-live', 'business_mutations': False}))
        return
    # Reserve the destination before any provider calls. Never overwrite prior evidence.
    with args.output.open('x') as output:
        report = {
            'dataset_version': dataset.dataset_version, 'dataset_sha256': fingerprint(raw),
            'reference_provenance': dataset.reference_provenance,
            'reference_as_of': dataset.reference_as_of,
            'started_at': datetime.now(UTC).isoformat(),
            'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'versions': {name: version(name) for name in ('openai-agents', 'openai', 'pymongo')},
            'planned_invocations': len(dataset.cases)*args.repeats,
            'inter_invocation_pause_seconds': args.pause_seconds,
            'attempts': [], 'summaries': {}, 'stopped_early': False,
            'token_usage': None, 'cost_usd': None,
            'limitations': [
                'Developer-authored synthetic references; not independent SME validation',
                'Operator-admitted owner identity; not a browser authentication test',
                'Fresh sessions with shared Engine memory enabled, not independent samples',
                'Exact text match is a regression metric, not general semantic correctness',
                'Tool parameters and usage not read from native traces in this increment',
                'No corpus ranking, cache, Matryoshka or LLM judge acceptance in this report',
                'At most 12 sequential Engine invocations; existing native budgets remain active',
                'Completed evaluator runtime reservations are released natively; durable history remains',
            ],
        }

        def save():
            output.seek(0)
            json.dump(report, output, indent=2, allow_nan=False)
            output.write('\n')
            output.truncate()
            output.flush()

        save()
        try:
            with MongoClient(os.environ['KNOWLEDGE_READER_URI'], timeoutMS=15000) as client:
                owner = client.telecom_demo_knowledge.owners.find_one({
                    'tenant_id': 'synthetic-telecom', 'owner_id': 'demo-document-owner', 'active': True})
            if not owner or len(owner['user_ids']) != 1:
                raise ValueError('Expected the admitted synthetic owner')
            actor = SimpleNamespace(user_id=owner['user_ids'][0], role='admin')
            engine = EngineAPI()
            service = JourneyService(SimpleNamespace(principal=lambda token: actor), engine)
            for case in dataset.cases:
                for repeat in range(args.repeats):
                    conversation = uuid4()
                    session = session_id(actor.user_id, conversation)
                    start = time.monotonic()
                    row = {'case_id': case.case_id, 'repeat': repeat + 1, 'session_id': session,
                           'execution_id': None, 'error_type': None}
                    state = None
                    try:
                        invoked = engine.invoke(actor.user_id, session, case.question)
                        row['execution_id'] = invoked['execution_id']
                        deadline = start + 180
                        while True:
                            state = service.present('operator-admitted-evaluation', row['execution_id'])
                            if state['status'] in ('completed', 'error', 'cancelled', 'suspended'):
                                break
                            if time.monotonic() >= deadline:
                                raise TimeoutError('Evaluation observation deadline')
                            time.sleep(2)
                    except Exception as error:
                        row['error_type'] = type(error).__name__
                        # An uncertain invoke is not resubmitted. Session ID supports native recovery.
                        state = None
                    row['elapsed_seconds'] = round(time.monotonic() - start, 3)
                    row['metrics'] = measure(case, state)
                    report['attempts'].append(row)
                    report['summaries'][case.case_id] = summarize([
                        item for item in report['attempts'] if item['case_id'] == case.case_id])
                    save()
                    print(json.dumps({'case': case.case_id, 'repeat': repeat + 1,
                                      'final_contract_valid': row['metrics']['final_contract_valid'],
                                      'error_type': row['error_type']}), flush=True)
                    if not row['metrics']['final_contract_valid']:
                        report['stopped_early'] = True
                        break
                    try:
                        row['runtime_release'] = release_completed_runtime(
                            engine, session, row['execution_id'])
                    except Exception as error:
                        row['runtime_release_error'] = type(error).__name__
                        report['stopped_early'] = True
                        save()
                        break
                    save()
                    if len(report['attempts']) < report['planned_invocations']:
                        time.sleep(args.pause_seconds)
                if report['stopped_early']:
                    break
        except Exception as error:
            report['setup_error_type'] = type(error).__name__
            report['stopped_early'] = True
        finally:
            report['completed_at'] = datetime.now(UTC).isoformat()
            report['not_attempted'] = report['planned_invocations'] - len(report['attempts'])
            save()
        passed = not report['stopped_early'] and all(
            row['metrics'][metric] is True for row in report['attempts']
            for metric in ('final_contract_valid', 'routing_match', 'outcome_completed',
                           'exact_reference_match'))
        raise SystemExit(0 if passed else 1)


if __name__ == '__main__':
    main()
