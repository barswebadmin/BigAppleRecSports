import pytest


@pytest.fixture(autouse=True)
def reset_client_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    yield

