"""Offline setup checks. Reports names/status only; never contacts application providers."""
import argparse
import json
import os
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configuration_checks(env, home):
    required = ['APP_MONGODB_URI', 'APP_MONGODB_HOST', 'APP_ORIGIN', 'APP_WEB_DIST']
    rows = []
    for flag in ('APP_JOURNEY_ENABLED', 'APP_KNOWLEDGE_ENABLED'):
        rows.append({'check':flag, 'ok':env.get(flag, 'false') in ('true', 'false')})
    if env.get('APP_JOURNEY_ENABLED') == 'true':
        rows.append({'check':'private_engine_cli_login_file',
                     'ok':(home / '.agentengine/auth.json').is_file()})
    if env.get('APP_KNOWLEDGE_ENABLED') == 'true':
        required += ['INGESTION_MONGODB_URI', 'KNOWLEDGE_PUBLISHER_URI',
                     'KNOWLEDGE_READER_URI', 'VOYAGE_API_KEY', 'VOYAGE_BASE_URL']
    rows += [{'check':name, 'ok':bool(env.get(name, '').strip())} for name in required]
    rows.append({'check':'approved_application_host',
                 'ok':env.get('APP_MONGODB_HOST') == 'openai-sdk.qrmdk.mongodb.net'})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', action='store_true',
                        help='Check injected variable presence; do not print or validate secrets remotely')
    args = parser.parse_args()
    rows = [{'check':'python_3_15_2', 'ok':sys.version_info[:3] == (3,15,2)}]
    for relative in ('uv.lock', 'apps/web/package-lock.json', 'apps/web/dist/index.html'):
        rows.append({'check':relative, 'ok':(ROOT / relative).is_file()})
    for package, expected in (('openai-agents','0.24.0'), ('openai','3.40.0'), ('pymongo','4.19.0')):
        try:
            installed = version(package)
        except PackageNotFoundError:
            installed = None
        rows.append({'check':package, 'ok':installed == expected})
    try:
        node = subprocess.run(['node','--version'],capture_output=True,text=True,timeout=5,check=True)
        parts = tuple(int(x) for x in node.stdout.strip().lstrip('v').split('.'))
        node_ok = (26,5,0) <= parts < (27,0,0)
    except (OSError, ValueError, subprocess.SubprocessError):
        node_ok = False
    rows.append({'check':'node_26_5_or_later_within_26', 'ok':node_ok})
    if args.configuration:
        rows += configuration_checks(os.environ, Path.home())
    report = {'status':'pass' if all(r['ok'] for r in rows) else 'incomplete', 'checks':rows,
              'provider_calls':0, 'database_writes':0,
              'limits':['Configuration presence is not credential, role, source-validity or provider-health proof',
                        'CLI login file may be expired; check Atlas/Engine with their official tools',
                        'Voice requires OPENAI_API_KEY; optional cache requires KNOWLEDGE_CACHE_URI']}
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['status']=='pass' else 1)


if __name__ == '__main__':
    main()
