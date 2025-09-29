import os
import pytest

from backend.config.slack import SlackConfig, SlackChannel, SlackGroup, SlackBot, SlackUser


def test_channels_expose_id_and_name():
    # JoeTest channel should have id and name
    assert hasattr(SlackChannel.JoeTest, "id")
    assert hasattr(SlackChannel.JoeTest, "name")
    assert isinstance(SlackChannel.JoeTest.id, str)
    assert SlackChannel.JoeTest.name.startswith("#")


def test_channels_all_mapping():
    all_channels = SlackConfig.Channels.all()
    # Expect friendly names as keys and _Channel instances as values
    assert "joe-test" in all_channels
    joe = all_channels["joe-test"]
    assert hasattr(joe, "id") and hasattr(joe, "name")


def test_groups_get_known_and_default():
    known = SlackGroup.get("dodgeball")
    assert isinstance(known, dict) and "id" in known and "name" in known

    unknown = SlackGroup.get("does-not-exist")
    assert unknown == {"id": "@here", "name": "@here"}


def test_users_all_mapping_structure():
    users = SlackUser.all()
    # PascalCase keys (e.g., 'Here'), with id and name fields
    assert "Here" in users
    assert users["Here"]["id"] == "@here"
    assert users["Here"]["name"] == "@here"


def test_bot_token_and_signing_secret_env(monkeypatch):
    # Set env vars for a specific bot (Registrations)
    monkeypatch.setenv("SLACK_BOT_TOKEN_REGISTRATIONS", "xoxb-registrations-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET_REGISTRATIONS", "registrations-secret")

    assert SlackBot.Registrations.token == "xoxb-registrations-token"
    assert SlackBot.Registrations.signing_secret == "registrations-secret"


