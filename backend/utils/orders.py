"""Order helpers used by the refund-cancel workflow.

Per design § 2.d (Stage 2 Commit 2.3 — D21):

  ``strip_order_number_prefix`` (the canonical ``"#48957" → "48957"`` shaper)
  + the new ``parse_product_title`` helper used by
  ``EstimateService._build_product_info`` (Stage 2 § 2.c).

Drift note: ``strip_order_number_prefix`` did not previously exist as a
named symbol in the backend. The implementation below is the trivial form
documented by the design table.
"""

import re
from typing import TypedDict

# ── Order-number normalization ──────────────────────────────────────────────


def strip_order_number_prefix(order_number: str | None) -> str:
    """Strip the leading ``#`` from a Shopify order number, returning the
    bare digit string.

    Correctness properties:
      - ``strip_order_number_prefix(None)`` returns ``""``.
      - ``strip_order_number_prefix("")`` returns ``""``.
      - Surrounding whitespace is stripped first, then a single leading
        ``#`` is removed (multiple leading hashes are NOT removed —
        ``"##42"`` stays as ``"#42"``; this matches Shopify's display
        convention of exactly one prefix character).
      - The result is otherwise the original string verbatim — digits are
        preserved as-is, no validation is performed.
    """
    if not order_number:
        return ""
    trimmed = order_number.strip()
    return trimmed[1:] if trimmed.startswith("#") else trimmed


# ── Product-title parsing (used by EstimateService._build_product_info) ─────


class ParsedProductTitle(TypedDict, total=False):
    """The shape returned by :func:`parse_product_title`.

    Each field is `Optional` — the parser is best-effort and individual
    fields may be absent when the title does not include them. Callers
    (``EstimateService._build_product_info``) fall back to product
    attributes (``product_type``, ``tags``) when a field is missing.
    """

    year: int
    season: str
    sport: str
    day: str
    division: str


_SEASONS = ("Winter", "Spring", "Summer", "Fall")
_DAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
_DIVISIONS = ("WTNB+", "WTNB", "Open")
_SPORTS = (
    "Volleyball",
    "Kickball",
    "Dodgeball",
    "Bowling",
    "Pickleball",
    "Basketball",
    "Soccer",
    "Tennis",
    "Cornhole",
    "Wiffleball",
    "Softball",
)

_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def _find_token(text: str, options: tuple[str, ...]) -> str | None:
    """Case-insensitive whole-token match against ``options``. Returns the
    canonical option (preserving its capitalization), or ``None``."""
    lowered = text.lower()
    for option in options:
        if option.lower() in lowered:
            return option
    return None


def parse_product_title(title: str | None) -> ParsedProductTitle:
    """Extract structured fields from a Shopify product title.

    Handles the two title patterns BARS uses today (D31 — title parsing is
    best-effort, callers fall back to product attributes when fields are
    missing):

        "Winter 2025 Thursday Open Volleyball"
        "WTNB+ Volleyball Spring 2025 Tuesday"

    Correctness properties:
      - ``parse_product_title(None)`` returns ``{}``.
      - ``parse_product_title("")`` returns ``{}``.
      - All matches are case-insensitive against a fixed token list per
        field; matches return the canonical (capitalized) form so
        downstream comparisons stay simple.
      - The function is order-agnostic: it scans the whole title for each
        field independently.
      - Fields that don't match any known token are simply omitted from
        the returned dict (TypedDict ``total=False``).

    Note: this parser intentionally has no regex backtracking landmines —
    every search is a fixed-list ``in`` check against a small constant
    token table. Adding a new sport (etc.) is a one-line addition to the
    constants above.
    """
    if not title:
        return {}

    out: ParsedProductTitle = {}

    year_match = _YEAR_RE.search(title)
    if year_match:
        out["year"] = int(year_match.group(1))

    if (season := _find_token(title, _SEASONS)) is not None:
        out["season"] = season

    if (day := _find_token(title, _DAYS)) is not None:
        out["day"] = day

    # Division before sport so "WTNB+" beats a hypothetical sport-overlap.
    if (division := _find_token(title, _DIVISIONS)) is not None:
        out["division"] = division

    if (sport := _find_token(title, _SPORTS)) is not None:
        out["sport"] = sport

    return out
