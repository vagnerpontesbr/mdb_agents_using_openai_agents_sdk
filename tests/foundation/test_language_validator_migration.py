"""The migration may issue only two reviewed collMod commands after every preflight."""

import copy
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from scripts import apply_language_validators as migration
from tests.foundation.conftest import URI


def setup(monkeypatch, tmp_path):
    proposal = json.loads(Path('compatibility/lang2c-validator-proposal.json').read_text())
    file = tmp_path / 'proposal.json'
    file.write_text(json.dumps(proposal))
    monkeypatch.setattr('sys.argv',
                        ['migration', '--proposal', str(file), '--apply-approved-change'])
    monkeypatch.setenv('MONGODB_URI', URI)
    client = MagicMock()
    client.__enter__.return_value = client
    db = client.telecom_demo_knowledge
    state = {row['collection']: {'validator': row['expected_before'],
             'validationLevel': 'strict', 'validationAction': 'error'}
             for row in proposal['commands']}
    collections = {}
    for name in state:
        collection = Mock()
        collection.options.side_effect = lambda name=name: copy.deepcopy(state[name])
        collection.count_documents.return_value = 0
        collections[name] = collection
    db.__getitem__.side_effect = collections.__getitem__

    def update(command):
        state[command['collMod']]['validator'] = copy.deepcopy(command['validator'])

    db.command.side_effect = update
    connection = Mock(return_value=client)
    monkeypatch.setattr(migration, 'connect', connection)
    return proposal, file, db, state, collections, connection


def test_missing_explicit_apply_flag_never_connects(monkeypatch, tmp_path):
    _, file, _, _, _, connection = setup(monkeypatch, tmp_path)
    monkeypatch.setattr('sys.argv', ['migration', '--proposal', str(file)])
    with pytest.raises(SystemExit):
        migration.main()
    connection.assert_not_called()


def test_scope_tampering_is_rejected_before_connection(monkeypatch, tmp_path):
    proposal, file, _, _, _, connection = setup(monkeypatch, tmp_path)
    proposal['commands'][0]['database'] = 'another-project'
    file.write_text(json.dumps(proposal))
    with pytest.raises(ValueError, match='differs'):
        migration.main()
    connection.assert_not_called()


@pytest.mark.parametrize('failure', ['drift', 'incompatible'])
def test_all_collections_preflight_before_any_write(monkeypatch, tmp_path, failure):
    _, _, db, state, collections, _ = setup(monkeypatch, tmp_path)
    if failure == 'drift':
        state['chunks']['validator'] = {'unexpected': True}
    else:
        collections['chunks'].count_documents.return_value = 1
    with pytest.raises(ValueError):
        migration.main()
    db.command.assert_not_called()


def test_exact_commands_only_and_partial_application_can_resume(monkeypatch, tmp_path):
    proposal, _, db, state, _, _ = setup(monkeypatch, tmp_path)
    first = proposal['commands'][0]
    state[first['collection']]['validator'] = first['command']['validator']
    migration.main()
    assert [call.args[0] for call in db.command.call_args_list] == [
        row['command'] for row in proposal['commands']]
