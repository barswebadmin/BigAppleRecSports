"""Pure refund-estimate math from season timing — no I/O, no Shopify deps.

Single source of truth for the refund/credit ladder. Consolidates three prior
implementations:

  - backend/registrations/utils/refund_calculator.py   (canonical, pure pydantic)
  - slack-apps/registrations-v2/lib/shopify/models/refunds.py  (v2, near-duplicate)
  - backend/shared/date_utils.py:calculate_refund_amount  (legacy procedural, buggy)

Pulled forward from each:
  - canonical: the WeekSchedule / SeasonDates / RefundResult model shape, the
    short-season skip (legacy was missing this — it would award a 50%/55% tier
    for short seasons that should have been capped one tier earlier).
  - v2: ``RefundTier.label`` for human-readable tier descriptions.
  - legacy: the distinct "no payment was made" case (separate from a generic
    error / no-season-info case) — surfaced via ``RefundResult.no_payment()``.

Markdown stays out of this module. ``RefundResult.message`` returns plain text;
Slack-bound consumers wrap with ``*…*`` themselves. Presentation is not domain logic.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pydantic import BaseModel


# ── Small helpers ───────────────────────────────────────────────────────────


def add_days(dt: datetime, days: int) -> datetime:
    return dt + timedelta(days=days)


def parse_date_mdy(date_str: str) -> datetime:
    """Parse ``M/D/YY`` or ``M/D/YYYY`` → UTC datetime at 07:00 (BARS convention)."""
    month, day, year = map(int, date_str.strip().split("/"))
    if year < 100:
        year += 2000
    return datetime(year, month, day, 7, 0, 0, tzinfo=timezone.utc)


def parse_csv_dates(csv: str | None) -> list[datetime]:
    """Parse a comma-separated list of M/D/YY dates; silently skip malformed entries."""
    if not csv:
        return []
    out: list[datetime] = []
    for part in csv.split(","):
        part = part.strip()
        if part and "/" in part:
            try:
                out.append(parse_date_mdy(part))
            except ValueError:
                continue
    return sorted(out)


def strip_html(html: str) -> str:
    """Strip tags, decode the two entities we actually see, collapse whitespace."""
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def ensure_utc(dt: datetime | None) -> datetime:
    """Default to ``now`` and coerce naïve datetimes to UTC."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ── Tier ladders ────────────────────────────────────────────────────────────


class RefundTier(BaseModel):
    percentage: int
    penalty: int

    @property
    def label(self) -> str:
        return f"{self.percentage}% after {self.penalty}% penalty"


REFUND_TIERS = [
    RefundTier(percentage=95, penalty=0),
    RefundTier(percentage=90, penalty=5),
    RefundTier(percentage=80, penalty=15),
    RefundTier(percentage=70, penalty=25),
    RefundTier(percentage=60, penalty=35),
    RefundTier(percentage=50, penalty=45),
]

CREDIT_TIERS = [
    RefundTier(percentage=100, penalty=0),
    RefundTier(percentage=95, penalty=5),
    RefundTier(percentage=85, penalty=15),
    RefundTier(percentage=75, penalty=25),
    RefundTier(percentage=65, penalty=35),
    RefundTier(percentage=55, penalty=45),
]

TIMING_LABELS = [
    "more than 2 weeks before week 1 started",
    "before week 1 started",
]


def timing_label(index: int) -> str:
    if index < len(TIMING_LABELS):
        return TIMING_LABELS[index]
    return f"after the start of week {index - 1}"


# ── Week schedule ───────────────────────────────────────────────────────────


class WeekSchedule(BaseModel):
    """Tier-cutoff datetimes for a season, including a synthetic 2-weeks-prior
    cutoff at the front. ``dates[i] < dates[i+1]``."""

    dates: list[datetime]

    @classmethod
    def build(
        cls,
        start: datetime,
        off_dates: list[datetime],
        num_weeks: int = 5,
    ) -> WeekSchedule:
        weeks = [add_days(start, 7 * i) for i in range(num_weeks)]

        # Each off-week pushes its own week (and every week after) forward by 7d.
        for off in sorted(off_dates):
            for i in range(len(weeks)):
                if weeks[i].date() == off.date():
                    weeks[i:] = [add_days(w, 7) for w in weeks[i:]]
                    break

        dates = [add_days(weeks[0], -14), *weeks]
        return cls(dates=dates)

    def week_index(self, submitted_at: datetime) -> int:
        """Index of the first cutoff the submission falls before, or
        ``len(self.dates)`` when it's past every cutoff.

        Unlike :meth:`resolve_tier`, this never caps or returns ``None`` — it's
        a pure "where does this date land" lookup, so callers can describe the
        week even for past-window submissions (which earn a 0% refund).
        """
        for i, cutoff in enumerate(self.dates):
            if submitted_at < cutoff:
                return i
        return len(self.dates)

    def resolve_tier(
        self,
        submitted_at: datetime,
        tiers: list[RefundTier],
        is_short_season: bool = False,
    ) -> tuple[RefundTier, int] | None:
        """Return the tier and its index, or ``None`` for "past all cutoffs".

        ``is_short_season`` skips the final (week-5) tier — short seasons end
        before week 5 starts, so awarding that tier would over-refund.
        """
        for i, cutoff in enumerate(self.dates):
            if submitted_at < cutoff:
                if is_short_season and i == 5:
                    continue
                if i < len(tiers):
                    return tiers[i], i
                break
        return None


# ── Season dates (parsed from product description HTML) ─────────────────────

# A single date in either format BARS uses in product descriptions:
#   numeric  -> 6/14/26  or  6/14/2026
#   longform -> June 14, 2026  (the comma is optional)
_DATE_TOKEN = r"\d{1,2}/\d{1,2}/\d{2,4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"

_LONGFORM_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y")


def parse_season_date(token: str) -> datetime | None:
    """Parse one date token (numeric or ``Month D, YYYY``) → UTC 07:00, or None."""
    token = token.strip()
    if "/" in token:
        try:
            return parse_date_mdy(token)
        except (ValueError, TypeError):
            return None
    for fmt in _LONGFORM_FORMATS:
        try:
            return datetime.strptime(token, fmt).replace(hour=7, tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _norm_date(dt: datetime) -> str:
    """Canonical ``M/D/YYYY`` string so downstream numeric parsers stay simple."""
    return f"{dt.month}/{dt.day}/{dt.year}"


SEASON_DATES_PATTERN = re.compile(
    r"Season Dates[^:\d]*[:\s]*?"
    rf"({_DATE_TOKEN})\s*[–—-]\s*"
    rf"({_DATE_TOKEN})"
    r"(?:\s*\((\d+)\s+weeks(?:,\s*off\s+([^)]+))?\))?",
    re.IGNORECASE,
)

# Off weeks are sometimes listed on their own line (e.g. "Off Dates: June 28,
# 2026") instead of inline in the "(N weeks, off …)" parenthetical. Capture the
# run of date tokens immediately after the label.
OFF_DATES_PATTERN = re.compile(
    rf"Off Dates[^:\d]*[:\s]+((?:(?:{_DATE_TOKEN})\s*,?\s*)+)",
    re.IGNORECASE,
)


class SeasonDates(BaseModel):
    start_date: str | None = None
    off_dates: str | None = None
    total_weeks: int | None = None

    @classmethod
    def from_html(cls, html: str) -> SeasonDates:
        """Pull season-start/off/weeks out of a Shopify product description.

        Handles both date formats BARS uses — numeric (``1/1/26``) and longform
        (``June 14, 2026``) — and off weeks given either inline (``… (5 weeks,
        off 1/15/26)``) or on a separate ``Off Dates:`` line. Start/off dates are
        normalized to ``M/D/YYYY`` so the schedule builder stays numeric-only.
        Returns an all-None instance when no season start can be parsed.
        """
        if not html:
            return cls()
        text = strip_html(html)
        match = SEASON_DATES_PATTERN.search(text)
        if not match:
            return cls()
        start = parse_season_date(match.group(1))
        if start is None:
            return cls()

        # Off dates: inline parenthetical and/or the standalone "Off Dates:" line.
        off_sources = [match.group(4) or ""]
        line_match = OFF_DATES_PATTERN.search(text)
        if line_match:
            off_sources.append(line_match.group(1))
        off_dates = [
            dt
            for src in off_sources
            for tok in re.findall(_DATE_TOKEN, src)
            if (dt := parse_season_date(tok))
        ]

        return cls(
            start_date=_norm_date(start),
            off_dates=", ".join(_norm_date(dt) for dt in off_dates) or None,
            total_weeks=int(match.group(3)) if match.group(3) else None,
        )

    def to_schedule(self) -> WeekSchedule:
        assert self.start_date is not None, "start_date required to build schedule"
        return WeekSchedule.build(parse_date_mdy(self.start_date), parse_csv_dates(self.off_dates))

    @property
    def is_short(self) -> bool:
        return self.total_weeks is not None and self.total_weeks <= 7


# ── Result + entry point ────────────────────────────────────────────────────


class EstimateTierKind(StrEnum):
    """Which percentage ladder to use."""

    REFUND_TO_ORIGINAL = "refund_to_original"
    STORE_CREDIT = "store_credit"


class RefundResult(BaseModel):
    success: bool
    amount: float
    percentage: int = 0
    penalty: int = 0
    timing: str = ""
    has_processing_fee: bool = False
    no_payment: bool = False
    """True when the order had no payment — distinguishes from "past all cutoffs"."""

    @property
    def message(self) -> str:
        if not self.success:
            return "Error calculating refund — check order and product"
        if self.no_payment:
            return "Estimated Refund Due: $0 (No payment was made for this order)"
        if self.amount == 0:
            return "Estimated Refund Due: $0 (No refund — request came after week 5)"
        fee = " + 5% processing fee" if self.has_processing_fee else ""
        return (
            f"Estimated Refund Due: ${self.amount:.2f}\n"
            f"(Submitted {self.timing}. "
            f"{self.percentage}% after {self.penalty}% penalty{fee})"
        )

    @classmethod
    def zero(cls, timing: str = "") -> RefundResult:
        return cls(success=True, amount=0, timing=timing)

    @classmethod
    def no_payment_made(cls) -> RefundResult:
        return cls(success=True, amount=0, no_payment=True)

    @classmethod
    def error(cls) -> RefundResult:
        return cls(success=False, amount=0)


def estimate_refund_due(
    season: SeasonDates,
    total_paid: float,
    tier_kind: EstimateTierKind,
    submitted_at: datetime | None = None,
) -> RefundResult:
    """Compute tier, amount, and a user-facing message from season + paid total.

    Branches:
      - ``total_paid == 0`` → :meth:`RefundResult.no_payment_made` (distinct UX).
      - ``total_paid < 0`` or no ``season.start_date`` → :meth:`RefundResult.error`.
      - past all tier cutoffs → :meth:`RefundResult.zero` ("after week 5").
      - otherwise → full result with tier, amount, timing label, fee flag.
    """
    if total_paid == 0:
        return RefundResult.no_payment_made()
    if not season.start_date or total_paid < 0:
        return RefundResult.error()

    submitted = ensure_utc(submitted_at)
    schedule = season.to_schedule()
    tiers = REFUND_TIERS if tier_kind == EstimateTierKind.REFUND_TO_ORIGINAL else CREDIT_TIERS

    resolved = schedule.resolve_tier(submitted, tiers, season.is_short)
    if resolved is None:
        return RefundResult.zero()

    tier, index = resolved
    return RefundResult(
        success=True,
        amount=(tier.percentage / 100) * total_paid,
        percentage=tier.percentage,
        penalty=tier.penalty,
        timing=timing_label(index),
        has_processing_fee=tier_kind == EstimateTierKind.REFUND_TO_ORIGINAL,
    )
