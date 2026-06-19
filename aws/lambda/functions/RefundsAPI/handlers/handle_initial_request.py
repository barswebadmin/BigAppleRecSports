"""Initial refund-request handler (``action=evaluate_refund``).

``handle_initial_request`` is pure domain logic. ``run_evaluate_refund`` is the
evaluate action entry: validate → handle → Slack POST → response dict.
"""

import json
import os
from functools import cache
from typing import Any

from models import (
    RefundEstimate,
    RefundRequest,
    RefundResponse,
    ShopifyOrder,
)
from registrations.refunds import (
    EstimateTierKind,
    RefundResult,
    SeasonDates,
    estimate_refund_due,
    timing_label,
)
from shopify_client import ShopifyClient
from slack_handler import post_to_slack

_REFUND_EVAL_TRIGGER_URL_ENV = "SLACK__REFUND_EVAL_TRIGGER_URL"


@cache
def _client() -> ShopifyClient:
    return ShopifyClient(
        api_token=os.environ["SHOPIFY__TOKEN__ADMIN"],
        api_version=os.environ["SHOPIFY__API_VERSION"],
        store_id=os.environ["SHOPIFY__STORE_ID"],
        location_id=os.environ.get("SHOPIFY__LOCATION_ID", ""),
    )


def _resolve_week_label(season: SeasonDates, submitted_at) -> str | None:
    if not season.start_date:
        return None
    return timing_label(season.to_schedule().week_index(submitted_at))


def _estimate(result: RefundResult) -> RefundEstimate:
    return RefundEstimate(
        success=result.success,
        amount=result.amount,
        percentage=result.percentage,
        penalty=result.penalty,
        timing=result.timing,
        has_processing_fee=result.has_processing_fee,
        no_payment=result.no_payment,
        message=result.message,
    )


def _echo(req: RefundRequest) -> dict:
    return {
        "email": req.email,
        "first_name": req.first_name,
        "last_name": req.last_name,
        "refund_to": req.refund_to,
        "notes": req.notes,
        "is_test": req.is_test,
    }


def run_evaluate_refund(payload: dict[str, Any]) -> dict[str, Any]:
    req = RefundRequest.model_validate(payload)
    result = handle_initial_request(req)
    response_payload = result.to_json()
    post_to_slack(
        req.slack_trigger_url or os.environ.get(_REFUND_EVAL_TRIGGER_URL_ENV),
        {"evaluation_json": json.dumps(response_payload, default=str)},
    )
    return response_payload


def handle_initial_request(req: RefundRequest) -> RefundResponse:
    if not req.order_number:
        return RefundResponse(
            **_echo(req),
            order_number="",
            order_id=None,
            order_found=False,
            validation_passed=False,
            warnings=["Order number was empty in the request"],
            error="order_number_missing",
        )

    raw = _client().get_order_by_name(name=req.order_number)
    if raw is None:
        return RefundResponse(
            **_echo(req),
            order_number=req.order_number,
            order_id=None,
            order_found=False,
            validation_passed=False,
            warnings=[f"No order found with name '{req.order_number}'"],
            error="order_not_found",
        )

    order = ShopifyOrder.from_codegen(raw)
    validation = req.validate_against_order(order)

    product = order.product
    league = product.league if product else None
    season_dates = product.season_dates if product else SeasonDates()
    submitted_at = req.submitted_at
    season_week_resolved = _resolve_week_label(season_dates, submitted_at)

    est_original = estimate_refund_due(
        season=season_dates,
        total_paid=order.refundable_balance,
        tier_kind=EstimateTierKind.REFUND_TO_ORIGINAL,
        submitted_at=submitted_at,
    )
    est_credit = estimate_refund_due(
        season=season_dates,
        total_paid=order.refundable_balance,
        tier_kind=EstimateTierKind.STORE_CREDIT,
        submitted_at=submitted_at,
    )

    warnings = list(validation.warnings)
    if order.total_refunded > 0 and order.refundable_balance > 0:
        warnings.append(f"Order has been partially refunded: ${order.total_refunded:.2f} of ${order.order_total:.2f}")
    if order.refundable_balance <= 0 and order.order_total > 0:
        warnings.append("Order has already been fully refunded")
    if order.is_cancelled:
        warnings.append(f"Order was cancelled at {order.cancelled_at.isoformat()}")

    return RefundResponse(
        **_echo(req),
        order_number=order.name,
        order_id=order.id,
        order_found=True,
        validation_passed=validation.all_passed,
        warnings=warnings,
        sport=league.sport if league else None,
        season=league.season if league else None,
        day=league.day if league else None,
        division=league.division if league else None,
        product_id=product.id if product else None,
        product_title=product.title if product else None,
        season_start_date=season_dates.start_date,
        season_week_resolved=season_week_resolved,
        email_matched_against=validation.email.matched_against,
        first_name_matched_against=validation.first_name.matched_against,
        last_name_matched_against=validation.last_name.matched_against,
        estimated_refund_to_original=_estimate(est_original),
        estimated_store_credit=_estimate(est_credit),
        order_total=order.order_total,
        total_refunded=order.total_refunded,
        refundable_balance=order.refundable_balance,
        is_cancelled=order.is_cancelled,
        transactions=order.transactions,
        currency_code=order.currency_code,
    )
