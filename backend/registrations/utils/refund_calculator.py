"""Pure refund **estimate** math from season timing (no I/O).

Behavior matches ``slack-apps/registrations-v2/lib/shopify/models/refunds.py``:
same regex, week boundaries, tier tables, short-season skip, and message shapes.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from pydantic import BaseModel


def add_days(dt: datetime, days: int) -> datetime:
    return dt + timedelta(days=days)


def parse_date_mdy(date_str: str) -> datetime:
    month, day, year = map(int, date_str.strip().split("/"))
    if year < 100:
        year += 2000
    return datetime(year, month, day, 7, 0, 0, tzinfo=timezone.utc)


def parse_csv_dates(csv: str | None) -> list[datetime]:
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
    text = re.sub(r"<[^>]+>", "", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


class RefundTier(BaseModel):
    percentage: int
    penalty: int


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


class WeekSchedule(BaseModel):
    dates: list[datetime]

    @classmethod
    def build(
        cls,
        start: datetime,
        off_dates: list[datetime],
        num_weeks: int = 5,
    ) -> WeekSchedule:
        weeks = [add_days(start, 7 * i) for i in range(num_weeks)]

        for off in sorted(off_dates):
            for i in range(len(weeks)):
                if weeks[i].date() == off.date():
                    weeks[i:] = [add_days(w, 7) for w in weeks[i:]]
                    break

        dates = [add_days(weeks[0], -14), *weeks]
        return cls(dates=dates)

    def resolve_tier(
        self,
        submitted_at: datetime,
        tiers: list[RefundTier],
        is_short_season: bool = False,
    ) -> tuple[RefundTier, int] | None:
        for i, cutoff in enumerate(self.dates):
            if submitted_at < cutoff:
                if is_short_season and i == 5:
                    continue
                if i < len(tiers):
                    return tiers[i], i
                break
        return None


SEASON_DATES_PATTERN = re.compile(
    r"Season Dates[^:\d]*[:\s]*?"
    r"(\d{1,2}/\d{1,2}/\d{2,4})\s*[–—-]\s*"
    r"(\d{1,2}/\d{1,2}/\d{2,4})"
    r"(?:\s*\((\d+)\s+weeks(?:,\s*off\s+([^)]+))?\))?",
    re.IGNORECASE,
)


class SeasonDates(BaseModel):
    start_date: str | None = None
    off_dates: str | None = None
    total_weeks: int | None = None

    @classmethod
    def from_html(cls, html: str) -> SeasonDates:
        if not html:
            return cls()
        match = SEASON_DATES_PATTERN.search(strip_html(html))
        if not match or not match.group(1) or "/" not in match.group(1):
            return cls()
        off = match.group(4)
        return cls(
            start_date=match.group(1),
            off_dates=off if off and "/" in off else None,
            total_weeks=int(match.group(3)) if match.group(3) else None,
        )

    def to_schedule(self) -> WeekSchedule:
        start = parse_date_mdy(self.start_date)
        return WeekSchedule.build(start, parse_csv_dates(self.off_dates))

    @property
    def is_short(self) -> bool:
        return self.total_weeks is not None and self.total_weeks <= 7


class EstimateTierKind(StrEnum):
    """Which percentage ladder to use (same split as slack ``RefundType``)."""

    REFUND_TO_ORIGINAL = "refund_to_original"
    STORE_CREDIT = "store_credit"


class RefundResult(BaseModel):
    success: bool
    amount: float
    percentage: int = 0
    penalty: int = 0
    timing: str = ""
    has_processing_fee: bool = False

    @property
    def message(self) -> str:
        if not self.success:
            return "Error calculating refund — check order and product"
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
    def error(cls) -> RefundResult:
        return cls(success=False, amount=0)


def ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def estimate_refund_due(
    season: SeasonDates,
    total_paid: float,
    tier_kind: EstimateTierKind,
    submitted_at: datetime | None = None,
) -> RefundResult:
    """Compute tier, amount, and user-facing message from parsed season + paid total.

    Preconditions (caller's responsibility): ``season.start_date`` is set when HTML matched;
    this function returns :meth:`RefundResult.error` if ``not season.start_date`` or
    ``total_paid <= 0``.
    """
    if not season.start_date or total_paid <= 0:
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
