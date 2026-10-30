"""Set only the four new workspace-scoped knowledge bindings, without exposing values."""

import os
import subprocess


def main():
    for name, source in [('KNOWLEDGE_READER_URI', 'KNOWLEDGE_READER_URI'),
                         ('INGESTION_MONGODB_URI', 'INGESTION_MONGODB_URI'),
                         ('KNOWLEDGE_VOYAGE_KEY', 'VOYAGE_API_KEY'),
                         ('KNOWLEDGE_VOYAGE_BASE', 'VOYAGE_BASE_URL')]:
        result = subprocess.run(['agentengine', 'secret', 'set', name, '--stdin',
            '--workspace-id', 'ws-6ae20f53f3b040aa65fa961a',
            '--base-url', 'https://agentengine.mongodb.com',
            '--org-id', '663e3089acf80f05b63effcf', '--project-id', '67b385a7976edf15ecc62e06',
            '--description', 'Phase 4 scoped knowledge tool binding', '--no-log'],
            input=os.environ[source], capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError('Workspace binding failed')
    print('Four knowledge bindings configured in agentsdk workspace; no project bindings changed')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Hosted binding configuration stopped; details suppressed')
        raise SystemExit(1) from None
