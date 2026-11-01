import pytest

from tests.foundation.conftest import PASSWORD, login

VALUES = {"display_name": "Synthetic User", "timezone": "America/Sao_Paulo", "locale": "pt-BR",
          "expected_revision": 0}


def test_legacy_defaults_save_reload_and_new_login(client, identity):
    assert client.get('/api/profile').status_code == 401
    assert client.post('/api/profile', json=VALUES).status_code == 401
    login(client)
    original = identity.store.get('admin@mongodb.com')
    profile = client.get('/api/profile').json()
    assert (profile['locale'], profile['timezone'], profile['revision']) == ('en-US', 'UTC', 0)
    response = client.post('/api/profile', json=VALUES)
    assert response.status_code == 200
    assert response.json()['revision'] == 1
    assert 'password_hash' not in response.text
    client.post('/api/logout', json={})
    login(client)
    assert client.get('/api/profile').json()['display_name'] == VALUES['display_name']
    stored = identity.store.get('admin@mongodb.com')
    assert all(stored[key] == original[key] for key in original)
    assert client.post('/api/profile', json=VALUES).status_code == 409
    assert client.get('/api/profile').json()['revision'] == 1


@pytest.mark.parametrize('extra', [
    {'role': 'admin'}, {'email': 'victim@example.test'}, {'user_id': 'victim'},
    {'locale': 'fr-FR'}, {'timezone': '../../etc/passwd'}, {'timezone': 'Mars/Olympus'},
    {'display_name': '   '}, {'display_name': 'a\x00b'}, {'display_name': 'a' * 81},
    {'expected_revision': True}, {'expected_revision': -1},
])
def test_invalid_or_privileged_profile_input_never_writes(client, identity, extra):
    login(client)
    assert client.post('/api/profile', json={**VALUES, **extra}).status_code == 400
    assert 'profile' not in identity.store.get('admin@mongodb.com')


def test_preferences_are_isolated_and_disabled_user_cannot_save(client, identity):
    login(client)
    client.post('/api/profile', json=VALUES)
    client.post('/api/users', json={'email': 'member@example.test', 'password': PASSWORD})
    client.post('/api/logout', json={})
    client.post('/api/login', json={'email': 'member@example.test', 'password': PASSWORD})
    assert client.get('/api/profile').json()['locale'] == 'en-US'
    result = client.post('/api/profile', json={**VALUES, 'locale': 'es-ES'})
    assert result.status_code == 200
    assert result.json()['role'] == 'user'
    assert identity.store.get('admin@mongodb.com')['profile']['locale'] == 'pt-BR'
    identity.store.users['member@example.test']['active'] = False
    assert client.post('/api/profile', json={**VALUES, 'expected_revision': 1}).status_code == 401
