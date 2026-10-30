import pytest
from fastapi.testclient import TestClient

from compatibility.demo_auth.sessions import SessionAuth
from telecom_app.api import create_app
from telecom_app.config import Settings
from tests.demo_auth.test_sessions import SessionStore

ORIGIN = "http://127.0.0.1:8000"
URI = "mongodb+srv://synthetic:synthetic@openai-sdk.qrmdk.mongodb.net/"
PASSWORD = "synthetic-test-only"


@pytest.fixture
def identity():
    store = SessionStore()
    auth = SessionAuth(store)
    auth.auth.bootstrap(PASSWORD)
    return auth


@pytest.fixture
def client(identity):
    with TestClient(create_app(Settings(URI), identity), base_url=ORIGIN,
                    headers={"Origin": ORIGIN}) as browser:
        yield browser


def login(client):
    result = client.post("/api/login", json={"email": "admin@mongodb.com", "password": PASSWORD})
    assert result.status_code == 200
    return result
