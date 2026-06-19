"""Parse sport / season / day / division tokens from a Shopify product handle."""

from __future__ import annotations

from dataclasses import dataclass

SPORTS = (
    "dodgeball",
    "kickball",
    "pickleball",
    "bowling",
    "basketball",
    "volleyball",
    "soccer",
    "softball",
)
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
SEASONS = ("spring", "summer", "fall", "winter")
DIVISIONS = ("wtnb+", "wtnb", "open")


@dataclass(frozen=True)
class League:
    sport: str | None
    season: str | None
    day: str | None
    division: str | None


def _find_in_tokens(needles: tuple[str, ...], tokens: list[str]) -> str | None:
    for needle in needles:
        if needle in tokens:
            return needle
    return None


def _division_tokens(tokens: list[str]) -> list[str]:
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if token.endswith("div") and len(token) > 3:
            expanded.append(token[:-3])
    return expanded


def league_from_handle(handle: str | None) -> League:
    if not handle:
        return League(None, None, None, None)
    tokens = [t.strip().lower() for t in handle.split("-") if t.strip()]
    div_pool = _division_tokens(tokens)
    sport = _find_in_tokens(SPORTS, tokens)
    day = _find_in_tokens(DAYS, tokens)
    season = _find_in_tokens(SEASONS, tokens)
    division = _find_in_tokens(DIVISIONS, div_pool)
    return League(
        sport=sport.title() if sport else None,
        season=season,
        day=day.title() if day else None,
        division=division,
    )
