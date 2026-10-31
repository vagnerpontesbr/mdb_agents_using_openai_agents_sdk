"""Read native trace metrics for recorded evaluation sessions, without copying trace payloads."""

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID

from telecom_app.journey import EngineAPI
from compatibility.demo_auth.engine import WORKSPACE

EXPECTED={'invoice':{'telco_read_invoice'},'sales':{'telco_offer_plan'},
          'mixed':{'telco_read_invoice','telco_offer_plan'},'knowledge':{'telco_search_knowledge'}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    source=json.loads(args.report.read_text())
    assert len(source['attempts'])<=12
    report={'checked_at':datetime.now(UTC).isoformat(),'source_report':args.report.name,
            'rows':[],'cost_usd':None,'limitations':[
                'Token counts cover observed native invoke_llm spans, not unobserved memory/provider work',
                'Tool arguments may be redacted; unavailable is not a successful parameter grade',
                'Native Engine traces remain primary; no input/output/span payloads are copied',
                'Null execution roots permit session-level accounting only, not verified execution attribution']}
    with args.output.open('x') as output:
        def save():
            output.seek(0);json.dump(report,output,indent=2);output.write('\n');output.truncate();output.flush()
        save()
        for attempt in source['attempts']:
            row={'case_id':attempt['case_id'],'execution_id':attempt['execution_id']}
            try:
                session=attempt['session_id']
                assert re.fullmatch(r'telco-[a-f0-9]{48}',session)
                if not attempt['execution_id']:
                    row['unavailable_reason']='no_execution_id'
                    report['rows'].append(row);save();continue
                execution=str(UUID(attempt['execution_id']))
                data=EngineAPI().call('traces?'+urlencode({'session_id':session,'workspace_id':WORKSPACE}))
                spans=data.get('traces')
                assert isinstance(spans,list) and len(spans)<=300 and data.get('count')==len(spans)
                scoped=[s for s in spans if s.get('session_id')==session
                        and s.get('root_execution_id') in (None, execution)]
                row['correlation']='session_only' if any(
                    s.get('root_execution_id') is None for s in scoped) else 'execution_and_session'
                tools=[s for s in scoped if str(s.get('name','')).startswith('telco_')]
                names=sorted({s['name'] for s in tools})
                model=[s.get('attributes',{}) for s in scoped if s.get('name')=='invoke_llm']
                counts={}
                for name,key in [('input','llm.usage.prompt_tokens'),('output','llm.usage.completion_tokens'),
                                 ('total','llm.usage.total_tokens')]:
                    values=[a.get(key) for a in model]
                    counts[name]=sum(values) if values and all(type(v) is int and v>=0 for v in values) else None
                row.update(native_span_count=len(scoped),tool_names=names,
                    tool_selection_match=set(names)==EXPECTED[attempt['case_id']] if scoped else None,
                    model_calls=len(model),tokens=counts,
                    parameter_accuracy=None,
                    argument_payloads_available=bool(tools) and all(s.get('attributes',{}).get('inputs')
                                                                   is not None for s in tools))
            except Exception as error:
                row['error_type']=type(error).__name__
            report['rows'].append(row);save()
    print(json.dumps({'observations':len(report['rows']),
                      'scoped_rows':sum(bool(r.get('native_span_count')) for r in report['rows'])}))


if __name__=='__main__': main()
