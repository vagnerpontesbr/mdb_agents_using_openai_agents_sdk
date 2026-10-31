"""Inject the approved Phase 5 scoped URIs into the private local env file."""

import os
from pathlib import Path
from urllib.parse import quote


def main():
    destination = Path('.env')
    source = Path('.env.phase5')
    if destination.is_symlink() or source.is_symlink():
        raise ValueError('Refusing symlinked credentials')
    credentials = dict(line.split('=', 1) for line in source.read_text().splitlines() if line)
    text = destination.read_text()
    existing = dict(line.split('=', 1) for line in text.splitlines()
                    if '=' in line and not line.lstrip().startswith('#'))
    additions = []
    for key, username in (
        ('KNOWLEDGE_CACHE_URI', 'telecom_knowledge_cache'),
        ('EVALUATION_MONGODB_URI', 'telecom_phase5_evaluator'),
    ):
        uri = ('mongodb+srv://' + username + ':' + quote(credentials[username], safe='')
               + '@openai-sdk.qrmdk.mongodb.net/?authSource=admin&retryWrites=true&w=majority')
        if key in existing:
            if existing[key] != uri:
                raise ValueError('Existing domain configuration differs')
        else:
            additions.append(key + '=' + uri)
    if additions:
        with destination.open('a') as stream:
            stream.write('\n' + '\n'.join(additions) + '\n')
    os.chmod(destination, 0o600)
    print('Scoped domain URIs configured privately; knowledge remains opt-in')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Private configuration stopped; details suppressed')
        raise SystemExit(1) from None
