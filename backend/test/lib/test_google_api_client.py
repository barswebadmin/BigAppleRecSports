"""
Unit tests for GoogleApiClient instantiation.

Covers all three credential-loading paths:
  1. sa_info= dict passed directly
  2. config= Config instance
  3. os.environ fallback (GOOGLE__SERVICE_ACCOUNT)

No network calls — google-auth and googleapiclient.discovery are mocked.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

# Minimal valid-looking SA dict (no real keys)
_SA = {
    "type": "service_account",
    "project_id": "test-project",
    "private_key_id": "key-id",
    "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----\n",
    "client_email": "test@test-project.iam.gserviceaccount.com",
    "client_id": "123456789",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
}


@pytest.fixture(autouse=True)
def _mock_google(monkeypatch):
    """Patch google-auth so no real credential objects are built."""
    fake_creds = MagicMock()
    with patch(
        "shared_utilities.clients.google_api_client.service_account.Credentials.from_service_account_info",
        return_value=fake_creds,
    ) as mock_from_info:
        yield mock_from_info, fake_creds


def _make_client(sa_info=None, config=None, env_sa=None):
    """Import fresh each time so env patches take effect."""
    from shared_utilities.clients.google_api_client import GoogleApiClient
    return GoogleApiClient(sa_info=sa_info, config=config)


# ── Path 1: sa_info= ──────────────────────────────────────────────────────────

def test_init_with_sa_info(_mock_google):
    mock_from_info, _ = _mock_google
    client = _make_client(sa_info=_SA)
    assert client._sa_info["project_id"] == "test-project"
    assert "subject" not in client._sa_info


def test_init_sa_info_strips_subject(_mock_google):
    sa = {**_SA, "subject": "someone@example.com"}
    client = _make_client(sa_info=sa)
    assert "subject" not in client._sa_info


# ── Path 2: config= ───────────────────────────────────────────────────────────

def test_init_with_config(_mock_google):
    config = MagicMock()
    config.google.service_account = _SA
    client = _make_client(config=config)
    assert client._sa_info["project_id"] == "test-project"


def test_init_config_takes_priority_over_env(_mock_google, monkeypatch):
    monkeypatch.setenv("GOOGLE__SERVICE_ACCOUNT", json.dumps({**_SA, "project_id": "from-env"}))
    config = MagicMock()
    config.google.service_account = {**_SA, "project_id": "from-config"}
    client = _make_client(config=config)
    assert client._sa_info["project_id"] == "from-config"


# ── Path 3: os.environ fallback ───────────────────────────────────────────────

def test_init_from_env(_mock_google, monkeypatch):
    monkeypatch.setenv("GOOGLE__SERVICE_ACCOUNT", json.dumps(_SA))
    client = _make_client()
    assert client._sa_info["project_id"] == "test-project"


def test_init_env_missing_raises(_mock_google, monkeypatch):
    monkeypatch.delenv("GOOGLE__SERVICE_ACCOUNT", raising=False)
    from shared_utilities.clients.google_api_client import GoogleApiClient
    with pytest.raises(RuntimeError, match="GOOGLE__SERVICE_ACCOUNT not set"):
        GoogleApiClient()


def test_init_env_invalid_json_raises(_mock_google, monkeypatch):
    monkeypatch.setenv("GOOGLE__SERVICE_ACCOUNT", "not-json{")
    from shared_utilities.clients.google_api_client import GoogleApiClient
    with pytest.raises(json.JSONDecodeError):
        GoogleApiClient()


# ── Credential caching ────────────────────────────────────────────────────────

def test_credentials_cached(_mock_google):
    mock_from_info, _ = _mock_google
    from shared_utilities.clients.google_api_client import GmailScopes
    client = _make_client(sa_info=_SA)
    scopes = [GmailScopes.readonly]

    c1 = client._credentials(scopes, "user@example.com")
    c2 = client._credentials(scopes, "user@example.com")

    assert c1 is c2
    assert mock_from_info.call_count == 1  # built once, reused


def test_credentials_different_subject(_mock_google):
    mock_from_info, _ = _mock_google
    from shared_utilities.clients.google_api_client import GmailScopes
    client = _make_client(sa_info=_SA)
    scopes = [GmailScopes.readonly]

    client._credentials(scopes, "user1@example.com")
    client._credentials(scopes, "user2@example.com")

    assert mock_from_info.call_count == 2
