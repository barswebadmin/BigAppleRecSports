"""Extract ``(sport, day, division)`` from a Shopify product.

Tags are checked first when present — the BARS team-products convention puts
sport/day/division on the product as tags like ``"kickball"``, ``"monday"``,
``"open"``. When tags don't supply them, fall back to title parsing.

Returns ``None`` for any field that can't be determined. Slack reviewers can
still act on a refund with partial program context; the lambda's job is to
surface what's available, not to require every field.
"""

from __future__ import annotations

import re
from typing import Protocol


SPORTS = ("dodgeball", "kickball", "pickleball", "bowling", "basketball",
          "volleyball", "soccer", "softball")
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
# Order matters: "wtnb+" must be matched before "wtnb" so the plus sign isn't lost.
DIVISIONS = ("wtnb+", "wtnb", "open")


class _Product(Protocol):
    title: str
    tags: list[str]


def _find_in_tokens(needles: tuple[str, ...], tokens: list[str]) -> str | None:
    """Return the first needle that appears as an exact lowercased tag."""
    lower = [t.strip().lower() for t in tokens]
    for needle in needles:
        if needle in lower:
            return needle
    return None


def _find_in_text(needles: tuple[str, ...], text: str) -> str | None:
    """Word-boundary scan for the first needle present in the text (case-insensitive).

    ``wtnb+`` is special-cased because ``+`` isn't a word character — using a
    plain word-boundary regex would never match it.
    """
    if not text:
        return None
    lower = text.lower()
    for needle in needles:
        if needle == "wtnb+":
            if "wtnb+" in lower:
                return needle
        elif re.search(r"\b" + re.escape(needle) + r"\b", lower):
            return needle
    return None


def extract_program(product: _Product | None) -> tuple[str | None, str | None, str | None]:
    """Return ``(sport, day, division)``. Any of the three may be ``None``.

    Tags take precedence: a registration product tagged ``kickball monday open``
    short-circuits the title parser entirely. When a tag is absent, fall back
    to matching against the product title.

    Values are returned title-cased for sport/day, lowercase for division
    (matches the convention the Slack Deno app already renders against).
    """
    if product is None:
        return None, None, None

    tags = list(getattr(product, "tags", None) or [])
    title = getattr(product, "title", "") or ""

    sport = _find_in_tokens(SPORTS, tags) or _find_in_text(SPORTS, title)
    day = _find_in_tokens(DAYS, tags) or _find_in_text(DAYS, title)
    division = _find_in_tokens(DIVISIONS, tags) or _find_in_text(DIVISIONS, title)

    return (
        sport.title() if sport else None,
        day.title() if day else None,
        division,  # lowercase per Slack convention ("wtnb+" / "wtnb" / "open")
    )
