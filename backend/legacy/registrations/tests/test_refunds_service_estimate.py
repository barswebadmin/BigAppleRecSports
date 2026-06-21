"""RefundsService.calculate_estimated_refund_due delegates to utils.refund_calculator."""

from datetime import datetime, timezone

import pytest
from services.refunds_service import RefundsService
from modules.refunds.refund_calculator import EstimateTierKind, SeasonDates, estimate_refund_due

_SEASON_HTML = "Season Dates 1/15/2025 – 3/15/2025"
_EARLY = datetime(2024, 12, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("html", "expected_pair"),
    [
        (None, (None, None)),
        ("", (None, None)),
        ("   \n\t  ", (None, None)),
    ],
)
def test_calculate_estimated_refund_due_no_season_source(html, expected_pair):
    svc = RefundsService()
    out = svc.calculate_estimated_refund_due(
        order_total=100.0,
        refund_type="store_credit",
        product_description_html=html,
        submitted_at=_EARLY,
    )
    assert out == expected_pair


def test_calculate_estimated_refund_due_matches_util_for_store_credit():
    svc = RefundsService()
    season = SeasonDates.from_html(_SEASON_HTML)
    util = estimate_refund_due(
        season,
        100.0,
        EstimateTierKind.STORE_CREDIT,
        submitted_at=_EARLY,
    )
    got_amount, got_msg = svc.calculate_estimated_refund_due(
        order_total=100.0,
        refund_type="store_credit",
        product_description_html=_SEASON_HTML,
        submitted_at=_EARLY,
    )
    assert util.success and got_amount == util.amount and got_msg == util.message


def test_calculate_estimated_refund_due_matches_util_for_original_payment_ladder():
    svc = RefundsService()
    season = SeasonDates.from_html(_SEASON_HTML)
    util = estimate_refund_due(
        season,
        200.0,
        EstimateTierKind.REFUND_TO_ORIGINAL,
        submitted_at=_EARLY,
    )
    got_amount, got_msg = svc.calculate_estimated_refund_due(
        order_total=200.0,
        refund_type="original_payment",
        product_description_html=_SEASON_HTML,
        submitted_at=_EARLY,
    )
    assert util.success and got_amount == util.amount and got_msg == util.message


def test_calculate_estimated_refund_due_non_positive_total_delegates_to_util_error():
    svc = RefundsService()
    got_amount, got_msg = svc.calculate_estimated_refund_due(
        order_total=0.0,
        refund_type="store_credit",
        product_description_html=_SEASON_HTML,
        submitted_at=_EARLY,
    )
    assert got_amount is None
    assert got_msg == "Error calculating refund — check order and product"
