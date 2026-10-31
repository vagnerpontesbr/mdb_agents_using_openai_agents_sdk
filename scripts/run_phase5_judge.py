"""Six opt-in offline judge calls over synthetic proposed calibration labels."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from openai import OpenAI

from telecom_app.evaluation import fingerprint
from telecom_app.evaluation_judge import MODEL, RUBRIC, grade


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-provider-calls',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    raw=Path('examples/telecom/evaluation/judge-calibration-v1.json').read_text()
    dataset=json.loads(raw)
    assert len(dataset['cases'])==6
    with args.output.open('x') as output:
        report={'started_at':datetime.now(UTC).isoformat(),'model':MODEL,
            'dataset_sha256':fingerprint(raw),'rubric_sha256':fingerprint(RUBRIC),
            'human_review_status':dataset['review_status'],'results':[],
            'limits':['Synthetic demo references; requester review is not external SME validation',
                      'Offline judge only; no production gate or authorization authority',
                      'Direct Responses API, store=false, no tools, no application trace export'],
            'cost_usd':None}
        def save():
            output.seek(0);json.dump(report,output,indent=2);output.write('\n');output.truncate();output.flush()
        save()
        # No retries; six sequential synthetic calls, 60 seconds and 1,200 output tokens each.
        with OpenAI(api_key=os.environ['OPENAI_API_KEY'],base_url='https://api.openai.com/v1',
                    max_retries=0,timeout=60) as client:
            for case in dataset['cases']:
                row={'case_id':case['id']}
                try:
                    judgment,usage=grade(client,question=case['question'],answer=case['answer'],
                        source=case['source'],current_reference=dataset['current_reference'])
                    row.update(judgment=judgment.model_dump(),usage=usage,
                        faithful_agreement=judgment.faithful_to_source==case['expected_faithful'],
                        current_agreement=judgment.correct_for_current_reference==case['expected_current_correct'])
                except Exception as error:
                    row.update(error_type=type(error).__name__,faithful_agreement=None,current_agreement=None)
                report['results'].append(row);save()
                print(json.dumps({'case_id':case['id'],'error_type':row.get('error_type')}),flush=True)
                if row.get('error_type'): break
        report['completed_at']=datetime.now(UTC).isoformat()
        report['not_attempted']=6-len(report['results']);save()


if __name__=='__main__':
    try: main()
    except Exception as error:
        print(json.dumps({'error_type':type(error).__name__,'details_suppressed':True}))
        raise SystemExit(1) from None
