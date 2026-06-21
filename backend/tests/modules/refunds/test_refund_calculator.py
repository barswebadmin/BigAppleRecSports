"""Behavioral tests for the consolidated refund calculator.

These tests exist for two reasons:
  1. Verify the math (tier resolution, short-season skip, no-payment branch).
  2. Give ``refund_calculator.py`` a real consumer so it isn't a graveyard
     module while backend / lambdas migrate to it at their own pace.

Run from repo root: ``uv run pytest lib/tests/``.
"""

from datetime import datetime, timezone

import pytest

from modules.refunds.refund_calculator import (
    CREDIT_TIERS,
    REFUND_TIERS,
    EstimateTierKind,
    RefundResult,
    RefundTier,
    SeasonDates,
    estimate_refund_due,
)


SEASON_HTML = "Season Dates 1/15/2025 – 3/15/2025"
SHORT_SEASON_HTML = "Season Dates 1/15/2025 – 2/26/2025 (6 weeks)"
SEASON_WITH_OFF_HTML = "Season Dates 1/15/2025 – 3/15/2025 (5 weeks, off 1/29/2025)"
# Longform dates + a standalone "Off Dates:" line (real Shopify product shape).
SEASON_LONGFORM_HTML = (
    "<p><strong>Season Dates</strong>: June 14, 2026 – August 23, 2026 (8 weeks)</p>"
    "<p><strong>Off Dates</strong>: June 28, 2026</p>"
)


def _at(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, 0, 0, tzinfo=timezone.utc)


# ── Tier ladder shape ──────────────────────────────────────────────────────


def test_refund_tier_label_format():
    assert REFUND_TIERS[0].label == "95% after 0% penalty"
    assert REFUND_TIERS[-1].label == "50% after 45% penalty"
    assert CREDIT_TIERS[0].label == "100% after 0% penalty"


def test_tier_ladders_have_expected_values():
    assert [t.percentage for t in REFUND_TIERS] == [95, 90, 80, 70, 60, 50]
    assert [t.penalty for t in REFUND_TIERS] == [0, 5, 15, 25, 35, 45]
    assert [t.percentage for t in CREDIT_TIERS] == [100, 95, 85, 75, 65, 55]
    assert [t.penalty for t in CREDIT_TIERS] == [0, 5, 15, 25, 35, 45]


# ── Season parse ───────────────────────────────────────────────────────────


def test_season_dates_from_html_basic():
    s = SeasonDates.from_html(SEASON_HTML)
    assert s.start_date == "1/15/2025"
    assert s.off_dates is None
    assert s.total_weeks is None


def test_season_dates_from_html_with_off_dates_and_weeks():
    s = SeasonDates.from_html(SEASON_WITH_OFF_HTML)
    assert s.start_date == "1/15/2025"
    assert s.off_dates == "1/29/2025"
    assert s.total_weeks == 5


def test_season_dates_from_html_returns_empty_on_garbage():
    s = SeasonDates.from_html("no dates here")
    assert s.start_date is None and s.off_dates is None and s.total_weeks is None


def test_season_dates_from_html_longform_dates_and_off_line():
    # Longform month names and a standalone "Off Dates:" line both parse, and
    # are normalized to M/D/YYYY so the schedule builder stays numeric-only.
    s = SeasonDates.from_html(SEASON_LONGFORM_HTML)
    assert s.start_date == "6/14/2026"
    assert s.off_dates == "6/28/2026"
    assert s.total_weeks == 8


def test_season_dates_longform_estimate_resolves_real_tier():
    # The bug this guards: a longform-date product used to error to $0 because
    # the season start couldn't be parsed.
    season = SeasonDates.from_html(SEASON_LONGFORM_HTML)
    r = estimate_refund_due(
        season, 115.0, EstimateTierKind.REFUND_TO_ORIGINAL, submitted_at=_at(2026, 6, 22)
    )
    assert r.success
    assert r.amount == pytest.approx(80.5)  # 70% tier in week 2


def test_week_index_reports_landing_week_including_past_window():
    # week_index never caps/returns None — past every cutoff it returns len(dates)
    # so diagnostics can still label the week for a 0% (past-window) request.
    schedule = SeasonDates.from_html(SEASON_HTML).to_schedule()
    assert schedule.week_index(_at(2024, 12, 1)) == 0  # > 2 weeks before
    assert schedule.week_index(_at(2025, 1, 16)) == 2  # within week 1
    assert schedule.week_index(_at(2025, 6, 1)) == len(schedule.dates)  # past all cutoffs


# ── Tier resolution across the timeline ────────────────────────────────────


@pytest.mark.parametrize(
    ("submitted", "expected_percentage", "expected_index"),
    [
        # 2025-01-15 is the start (07:00 UTC); cutoffs at -14d, start, +7d, +14d, +21d, +28d.
        (_at(2024, 12, 1),  95, 0),  # > 2 weeks before week 1
        (_at(2025, 1, 5),   90, 1),  # in the 2-week pre-window
        (_at(2025, 1, 16),  80, 2),  # after start (within week 1)
        (_at(2025, 1, 23),  70, 3),  # after week 2 start
        (_at(2025, 1, 30),  60, 4),  # after week 3 start
        (_at(2025, 2, 6),   50, 5),  # after week 4 start
    ],
)
def test_estimate_refund_due_resolves_correct_refund_tier(submitted, expected_percentage, expected_index):
    season = SeasonDates.from_html(SEASON_HTML)
    r = estimate_refund_due(season, 100.0, EstimateTierKind.REFUND_TO_ORIGINAL, submitted_at=submitted)
    assert r.success
    assert r.percentage == expected_percentage
    assert r.amount == pytest.approx(expected_percentage)  # 100.0 * pct/100
    assert r.has_processing_fee is True


def test_estimate_refund_due_past_all_cutoffs_returns_zero():
    season = SeasonDates.from_html(SEASON_HTML)
    r = estimate_refund_due(season, 100.0, EstimateTierKind.REFUND_TO_ORIGINAL, submitted_at=_at(2025, 4, 1))
    assert r.success and r.amount == 0 and not r.no_payment
    assert "after week 5" in r.message


def test_store_credit_uses_credit_ladder_and_no_processing_fee():
    season = SeasonDates.from_html(SEASON_HTML)
    r = estimate_refund_due(season, 100.0, EstimateTierKind.STORE_CREDIT, submitted_at=_at(2024, 12, 1))
    assert r.success
    assert r.percentage == 100
    assert r.has_processing_fee is False
    assert "processing fee" not in r.message


# ── Distinct early-exit branches ───────────────────────────────────────────


def test_zero_payment_returns_no_payment_branch_not_error():
    season = SeasonDates.from_html(SEASON_HTML)
    r = estimate_refund_due(season, 0.0, EstimateTierKind.STORE_CREDIT, submitted_at=_at(2024, 12, 1))
    assert r.success is True
    assert r.no_payment is True
    assert r.amount == 0
    assert r.message == "Estimated Refund Due: $0 (No payment was made for this order)"


def test_negative_payment_returns_error():
    season = SeasonDates.from_html(SEASON_HTML)
    r = estimate_refund_due(season, -1.0, EstimateTierKind.STORE_CREDIT, submitted_at=_at(2024, 12, 1))
    assert r.success is False
    assert r.message == "Error calculating refund — check order and product"


def test_missing_season_start_returns_error_even_with_payment():
    r = estimate_refund_due(SeasonDates(), 100.0, EstimateTierKind.STORE_CREDIT, submitted_at=_at(2024, 12, 1))
    assert r.success is False


# ── Short-season behavior ──────────────────────────────────────────────────


def test_short_season_skips_final_tier():
    """A 6-week season is "short" (≤7 weeks). The week-5 tier (index 5) must
    be skipped, falling through to past-all-cutoffs and returning $0."""
    season = SeasonDates.from_html(SHORT_SEASON_HTML)
    assert season.is_short is True
    # Just barely into "after week 4 started" — without the short-season skip
    # this would award the 50% tier. With it, falls through to zero.
    r = estimate_refund_due(season, 100.0, EstimateTierKind.REFUND_TO_ORIGINAL, submitted_at=_at(2025, 2, 6))
    assert r.success and r.amount == 0


def test_normal_season_does_not_skip_final_tier():
    """Sanity check: the same time-of-submission for a NON-short season awards
    the 50% tier, confirming the short-season skip is the active discriminator."""
    season = SeasonDates.from_html(SEASON_HTML)  # no (N weeks) marker -> is_short False
    assert season.is_short is False
    r = estimate_refund_due(season, 100.0, EstimateTierKind.REFUND_TO_ORIGINAL, submitted_at=_at(2025, 2, 6))
    assert r.success and r.percentage == 50


# ── Off-date adjustment ────────────────────────────────────────────────────


def test_off_date_shifts_subsequent_weeks_forward():
    """With an off-week at 1/29, the week-3 cutoff moves from 1/29 → 2/5.
    A submission on 1/30 should resolve to the same tier as 1/22 (the
    pre-off-date schedule's week-3 boundary)."""
    season = SeasonDates.from_html(SEASON_WITH_OFF_HTML)
    r_post_off = estimate_refund_due(season, 100.0, EstimateTierKind.REFUND_TO_ORIGINAL, submitted_at=_at(2025, 1, 30))
    # 1/30 is now still in the week-2 window (because the originally-week-3 cutoff shifted to 2/5)
    assert r_post_off.success and r_post_off.percentage == 70


# ── Result helpers ─────────────────────────────────────────────────────────


def test_refund_result_message_for_normal_outcome():
    r = RefundResult(success=True, amount=85.0, percentage=85, penalty=15, timing="before week 1 started")
    assert "Estimated Refund Due: $85.00" in r.message
    assert "85% after 15% penalty" in r.message
    assert "processing fee" not in r.message  # has_processing_fee=False


def test_refund_result_message_includes_processing_fee_when_flagged():
    r = RefundResult(
        success=True, amount=85.0, percentage=85, penalty=15,
        timing="before week 1 started", has_processing_fee=True,
    )
    assert "+ 5% processing fee" in r.message


def test_refund_result_helpers():
    assert RefundResult.error().success is False
    assert RefundResult.zero().success is True and RefundResult.zero().amount == 0
    assert RefundResult.no_payment_made().no_payment is True
