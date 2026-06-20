"""Tests for shared_utilities.slack_config."""

import pytest

from shared_utilities.slack_config import (
    SlackConfig,
    parse_handle,
    resolve_slack_config,
    slack_config_from_handle,
)


class TestParseHandle:
    def test_standard_open(self):
        result = parse_handle("2026-spring-kickball-thursday-opendiv")
        assert result == {
            "year": "2026",
            "season": "spring",
            "sport": "kickball",
            "day": "thursday",
            "division": "open",
        }

    def test_wtnb(self):
        result = parse_handle("2026-spring-kickball-thursday-wtnbdiv")
        assert result["division"] == "wtnb"

    def test_too_few_parts(self):
        with pytest.raises(ValueError, match="has 3 parts"):
            parse_handle("2026-spring-kickball")

    def test_missing_div_suffix(self):
        with pytest.raises(ValueError, match="must end with 'div'"):
            parse_handle("2026-spring-kickball-thursday-open")


class TestSlackConfigFromHandle:
    def test_open_division(self):
        cfg = slack_config_from_handle("2026-spring-kickball-thursday-opendiv")
        assert cfg.bot_name == "registrations"
        assert cfg.channel_name == "kickball-thursday-open"
        assert cfg.tag_target == "@kickball-thursday-open-team"

    def test_wtnb_division(self):
        cfg = slack_config_from_handle("2026-spring-dodgeball-monday-wtnbdiv")
        assert cfg.channel_name == "dodgeball-monday-wtnb"
        assert cfg.tag_target == "@dodgeball-monday-wtnb-team"


class TestResolveSlackConfig:
    def test_handle_only(self):
        cfg = resolve_slack_config(handle="2026-spring-kickball-thursday-opendiv")
        assert cfg.bot_name == "registrations"
        assert cfg.channel_name == "kickball-thursday-open"
        assert cfg.tag_target == "@kickball-thursday-open-team"

    def test_override_bot(self):
        cfg = resolve_slack_config(
            handle="2026-spring-kickball-thursday-opendiv",
            overrides={"botName": "exec"},
        )
        assert cfg.bot_name == "exec"
        assert cfg.channel_name == "kickball-thursday-open"

    def test_override_channel(self):
        cfg = resolve_slack_config(
            handle="2026-spring-kickball-thursday-opendiv",
            overrides={"channelName": "custom-channel"},
        )
        assert cfg.channel_name == "custom-channel"
        assert cfg.tag_target == "@kickball-thursday-open-team"

    def test_full_override_no_handle(self):
        cfg = resolve_slack_config(
            overrides={
                "botName": "web",
                "channelName": "my-channel",
                "tagTarget": "@my-team",
            },
        )
        assert cfg.bot_name == "web"
        assert cfg.channel_name == "my-channel"
        assert cfg.tag_target == "@my-team"

    def test_no_handle_partial_override_fails(self):
        with pytest.raises(ValueError):
            resolve_slack_config(overrides={"botName": "web"})


class TestSlackConfigValidation:
    def test_empty_bot_name_fails(self):
        with pytest.raises(ValueError):
            SlackConfig(bot_name="", channel_name="ch", tag_target="@t")

    def test_whitespace_only_fails(self):
        with pytest.raises(ValueError):
            SlackConfig(bot_name="  ", channel_name="ch", tag_target="@t")

    def test_to_dict(self):
        cfg = SlackConfig(bot_name="registrations", channel_name="ch", tag_target="@t")
        d = cfg.to_dict()
        assert d == {"botName": "registrations", "channelName": "ch", "tagTarget": "@t"}
