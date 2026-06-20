"""Refund calculation and analysis for BARS registrations.

Public API:
    - estimate_refund_due: Compute refund amount from season dates and payment.
    - SeasonDates: Parsed season start/off/weeks from product description HTML.
    - RefundResult: Result of estimate calculation with amount, timing, message.
    - EstimateTierKind: Which percentage ladder to use (refund vs store credit).
    - RefundTier: A single tier (percentage, penalty) in the ladder.
    - WeekSchedule: Tier-cutoff datetimes for a season.
    - timing_label: Human-readable label for a tier index.

Tier ladders:
    - REFUND_TIERS: 95 / 90 / 80 / 70 / 60 / 50 (refund to original payment).
    - CREDIT_TIERS: 100 / 95 / 85 / 75 / 65 / 55 (store credit).

Helpers (exported for consumers that need lower-level access):
    - parse_date_mdy, parse_csv_dates, parse_season_date
    - strip_html, ensure_utc, add_days
"""

from lib.domain.registrations.refunds.refund_calculator import (
    CREDIT_TIERS,
    REFUND_TIERS,
    TIMING_LABELS,
    EstimateTierKind,
    RefundResult,
    RefundTier,
    SeasonDates,
    WeekSchedule,
    add_days,
    ensure_utc,
    estimate_refund_due,
    parse_csv_dates,
    parse_date_mdy,
    parse_season_date,
    strip_html,
    timing_label,
)
