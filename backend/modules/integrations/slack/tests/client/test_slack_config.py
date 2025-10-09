import os
import pytest

from config import config


def test_channels_expose_id_and_name():
    # JoeTest channel should have id and name
    assert hasattr(config.slack.Channels.JoeTest, "id")
    assert hasattr(config.slack.Channels.JoeTest, "name")
    assert isinstance(config.slack.Channels.JoeTest.id, str)
    assert config.slack.Channels.JoeTest.name.startswith("#")


def test_channels_all_mapping():
    all_channels = SlackConfig.Channels.all()
    # Expect friendly names as keys and _Channel instances as values
    assert "joe-test" in all_channels
    joe = all_channels["joe-test"]
    assert hasattr(joe, "id") and hasattr(joe, "name")


def test_groups_get_known_and_default():
    known = config.slack.Groups.get("dodgeball")
    assert isinstance(known, dict) and "id" in known and "name" in known

    unknown = config.slack.Groups.get("does-not-exist")
    assert unknown == {"id": "@here", "name": "@here"}


def test_users_all_mapping_structure():
    users = config.slack.Users.all()
    # PascalCase keys (e.g., 'Here'), with id and name fields
    assert "Here" in users
    assert users["Here"]["id"] == "@here"
    assert users["Here"]["name"] == "@here"


def test_bot_token_and_signing_secret_env(monkeypatch):
    # Set env vars for a specific bot (Registrations)
    monkeypatch.setenv("SLACK_BOT_TOKEN_REGISTRATIONS", "xoxb-registrations-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET_REGISTRATIONS", "registrations-secret")

    assert config.slack.Bots.Registrations.token == "xoxb-registrations-token"
    assert config.slack.Bots.Registrations.signing_secret == "registrations-secret"


