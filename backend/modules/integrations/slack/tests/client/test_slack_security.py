import hashlib
import hmac
import os

import pytest

from new_structure_target.clients.slack.core.slack_security import SlackSecurity


def _slack_signature(secret: str, body: bytes, timestamp: str) -> str:
    base = f"v0:{timestamp}:{body.decode('utf-8')}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()
    return f"v0={digest}"


@pytest.fixture()
def sample_body() -> bytes:
    return b'{"type":"url_verification","token":"abc","challenge":"xyz"}'


def test_slack_signature_test_env_common_secret(sample_body: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SLACK_TEST_SIGNING_SECRET", "test_secret_ABC123")
    ts = "1234567890"
    sig = _slack_signature("test_secret_ABC123", sample_body, ts)

    sec = SlackSecurity()
    assert sec.verify_slack_signature(sample_body, ts, sig) is True


def test_slack_signature_staging_specific_bot(sample_body: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    # Simulate SlackConfig.Bots.Registrations.signing_secret reading from env via SlackConfig
    monkeypatch.setenv("SLACK_SIGNING_SECRET_REGISTRATIONS", "reg_secret_456")
    ts = "1700000000"
    sig = _slack_signature("reg_secret_456", sample_body, ts)

    sec = SlackSecurity(bot="Registrations")
    assert sec.verify_slack_signature(sample_body, ts, sig) is True


def test_slack_signature_staging_try_all_bots(sample_body: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    # Provide only Dev secret; no bot passed, so it should try all and match Dev
    monkeypatch.setenv("SLACK_SIGNING_SECRET_DEV", "dev_secret_789")
    ts = "1700000001"
    sig = _slack_signature("dev_secret_789", sample_body, ts)

    sec = SlackSecurity()
    assert sec.verify_slack_signature(sample_body, ts, sig) is True


def test_slack_signature_invalid(sample_body: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("SLACK_SIGNING_SECRET_REGISTRATIONS", "reg_secret_456")
    ts = "1700000002"
    bad_sig = _slack_signature("wrong_secret", sample_body, ts)

    sec = SlackSecurity(bot="Registrations")
    assert sec.verify_slack_signature(sample_body, ts, bad_sig) is False
