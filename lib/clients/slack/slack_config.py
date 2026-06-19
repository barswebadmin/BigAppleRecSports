"""
Resolve Slack notification config from a Shopify product handle.

Handle format: {year}-{season}-{sport}-{day}-{division}div
    e.g. 2026-spring-kickball-thursday-opendiv

Derived Slack targets:
    channel:   #{sport}-{day}-{division}   e.g. #kickball-thursday-open
    tagTarget: @{sport}-{day}-{division}-team  e.g. @kickball-thursday-open-team
    botName:   registrations (default)
"""

from typing import Any

from pydantic import BaseModel, field_validator


_DEFAULT_BOT = "registrations"


class SlackConfig(BaseModel):
    """Validated Slack notification target."""

    bot_name: str
    channel_name: str
    tag_target: str

    @field_validator("bot_name", "channel_name", "tag_target")
    @classmethod
    def must_be_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()

    def to_dict(self) -> dict[str, str]:
        return {
            "botName": self.bot_name,
            "channelName": self.channel_name,
            "tagTarget": self.tag_target,
        }


def parse_handle(handle: str) -> dict[str, str]:
    """Parse a Shopify product handle into its components.

    Expected: {year}-{season}-{sport}-{day}-{division}div
    Returns dict with keys: year, season, sport, day, division
    Raises ValueError on invalid format.
    """
    parts = handle.split("-")
    if len(parts) < 5:
        raise ValueError(
            f"Handle {handle!r} has {len(parts)} parts, expected at least 5: "
            "year-season-sport-day-divisiondiv"
        )

    year, season, sport, day = parts[0], parts[1], parts[2], parts[3]
    division_raw = "-".join(parts[4:])

    if not division_raw.endswith("div"):
        raise ValueError(
            f"Handle {handle!r} division segment {division_raw!r} "
            "must end with 'div'"
        )

    division = division_raw[: -len("div")]
    return {
        "year": year,
        "season": season,
        "sport": sport,
        "day": day,
        "division": division,
    }


def slack_config_from_handle(handle: str) -> SlackConfig:
    """Derive a SlackConfig from a product handle.

    channel:   #{sport}-{day}-{division}
    tagTarget: @{sport}-{day}-{division}-team
    botName:   registrations
    """
    h = parse_handle(handle)
    sport = h["sport"]
    day = h["day"]
    division = h["division"]

    channel = f"{sport}-{day}-{division}"
    tag_target = f"@{sport}-{day}-{division}-team"

    return SlackConfig(
        bot_name=_DEFAULT_BOT,
        channel_name=channel,
        tag_target=tag_target,
    )


def resolve_slack_config(
    handle: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> SlackConfig:
    """Build a SlackConfig from a product handle, with optional per-field overrides.

    Priority: explicit override > handle-derived > default bot name.
    If no handle and no overrides, raises ValueError.
    """
    overrides = overrides or {}

    if handle:
        base = slack_config_from_handle(handle)
    else:
        base = SlackConfig(
            bot_name=_DEFAULT_BOT,
            channel_name=overrides.get("channelName", ""),
            tag_target=overrides.get("tagTarget", ""),
        )

    return SlackConfig(
        bot_name=overrides.get("botName", base.bot_name),
        channel_name=overrides.get("channelName", base.channel_name),
        tag_target=overrides.get("tagTarget", base.tag_target),
    )
