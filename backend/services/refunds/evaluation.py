"""Build Slack `RefundEvaluationPayload` wire dicts (snake_case JSON)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from box import Box

from lib.domain.registrations.refunds import (
    EstimateTierKind,
    RefundResult,
    SeasonDates,
    estimate_refund_due,
    timing_label,
)
from services.refunds.league_from_handle import league_from_handle
from services.refunds.matching import OrderMatchResult
from services.refunds.requests import RefundSubmitRequest


def refund_result_to_estimate_dict(r: RefundResult) -> dict[str, Any]:
    return {
        "success": r.success,
        "amount": float(r.amount),
        "percentage": r.percentage,
        "penalty": r.penalty,
        "timing": r.timing or None,
        "has_processing_fee": r.has_processing_fee,
        "no_payment": r.no_payment,
        "message": r.message,
    }


def order_refund_facts(order: Box) -> tuple[float, float, float, str | None]:
    order_total = (
        float(order.total_price_set.shop_money.amount) if order.total_price_set and order.total_price_set.shop_money else 0.0
    )
    tr = order.total_refunded_set
    total_refunded = (
        float(tr.shop_money.amount)
        if tr and tr.shop_money and tr.shop_money.amount is not None
        else 0.0
    )
    refundable = max(0.0, order_total - total_refunded)
    currency = (
        order.total_price_set.shop_money.currency_code
        if order.total_price_set and order.total_price_set.shop_money
        else None
    )
    return order_total, total_refunded, refundable, currency


def transactions_wire(order: Box) -> list[dict[str, Any]]:
    raw = order.transactions or []
    out: list[dict[str, Any]] = []
    for t in raw:
        parent = getattr(t, "parent_transaction", None)
        parent_id = parent.id if parent else None
        out.append(
            {
                "id": t.id,
                "kind": str(t.kind) if t.kind is not None else "",
                "status": str(t.status) if t.status is not None else "",
                "gateway": t.gateway,
                "parent_id": parent_id,
            }
        )
    return out


def resolve_week_label(season: SeasonDates, submitted_at: datetime) -> str | None:
    if not season.start_date:
        return None
    idx = season.to_schedule().week_index(submitted_at)
    return timing_label(idx)


def build_found_payload(
    order: Box,
    submit: RefundSubmitRequest,
    *,
    season: SeasonDates,
    est_original: RefundResult,
    est_credit: RefundResult,
    validation: OrderMatchResult,
) -> dict[str, Any]:
    order_total, total_refunded, refundable, currency = order_refund_facts(order)
    product = None
    if order.line_items:
        product = order.line_items[0].product
    handle = product.handle if product else None
    league = league_from_handle(handle)
    submitted_at = submit.submitted_at
    assert submitted_at is not None
    season_week = resolve_week_label(season, submitted_at)

    warnings = list(validation.warnings())
    if total_refunded > 0 and refundable > 0:
        warnings.append(
            f"Order has been partially refunded: ${total_refunded:.2f} of ${order_total:.2f}"
        )
    if refundable <= 0 and order_total > 0:
        warnings.append("Order has already been fully refunded")
    if order.cancelled_at:
        warnings.append(f"Order was cancelled at {order.cancelled_at}")

    return {
        "is_test": submit.is_test,
        "email": submit.email,
        "first_name": submit.first_name,
        "last_name": submit.last_name,
        "refund_to": submit.refund_to,
        "notes": submit.notes,
        "phone": submit.phone,
        "sport": league.sport,
        "season": league.season,
        "day": league.day,
        "division": league.division,
        "product_id": product.id if product else None,
        "product_title": product.title if product else None,
        "order_number": order.name,
        "order_id": order.id,
        "order_found": True,
        "order_total": order_total,
        "total_refunded": total_refunded,
        "refundable_balance": refundable,
        "is_cancelled": order.cancelled_at is not None,
        "validation_passed": validation.all_passed,
        "warnings": warnings,
        "email_matched_against": validation.email[2],
        "first_name_matched_against": validation.first_name[2],
        "last_name_matched_against": validation.last_name[2],
        "season_start_date": season.start_date,
        "season_week_resolved": season_week,
        "estimated_refund_to_original": refund_result_to_estimate_dict(est_original),
        "estimated_store_credit": refund_result_to_estimate_dict(est_credit),
        "transactions": transactions_wire(order),
        "currency_code": currency,
        "error": None,
    }


def build_not_found_payload(submit: RefundSubmitRequest, *, error: str) -> dict[str, Any]:
    display = submit.order_number_display or (submit.id or "")
    return {
        "is_test": submit.is_test,
        "email": submit.email,
        "first_name": submit.first_name,
        "last_name": submit.last_name,
        "refund_to": submit.refund_to,
        "notes": submit.notes,
        "phone": submit.phone,
        "sport": None,
        "season": None,
        "day": None,
        "division": None,
        "product_id": None,
        "product_title": None,
        "order_number": display,
        "order_id": None,
        "order_found": False,
        "order_total": None,
        "total_refunded": None,
        "refundable_balance": None,
        "is_cancelled": None,
        "validation_passed": False,
        "warnings": [f"No order found for {display!r}"] if display else ["No order identifier in request"],
        "email_matched_against": None,
        "first_name_matched_against": None,
        "last_name_matched_against": None,
        "season_start_date": None,
        "season_week_resolved": None,
        "estimated_refund_to_original": None,
        "estimated_store_credit": None,
        "transactions": [],
        "currency_code": None,
        "error": error,
    }


def build_parse_error_payload(
    order: Box,
    submit: RefundSubmitRequest,
    *,
    validation: OrderMatchResult,
    note: str,
) -> dict[str, Any]:
    order_total, total_refunded, refundable, currency = order_refund_facts(order)
    return {
        "is_test": submit.is_test,
        "email": submit.email,
        "first_name": submit.first_name,
        "last_name": submit.last_name,
        "refund_to": submit.refund_to,
        "notes": submit.notes,
        "phone": submit.phone,
        "sport": None,
        "season": None,
        "day": None,
        "division": None,
        "product_id": None,
        "product_title": None,
        "order_number": order.name,
        "order_id": order.id,
        "order_found": True,
        "order_total": order_total,
        "total_refunded": total_refunded,
        "refundable_balance": refundable,
        "is_cancelled": order.cancelled_at is not None,
        "validation_passed": validation.all_passed,
        "warnings": [*validation.warnings(), note],
        "email_matched_against": validation.email[2],
        "first_name_matched_against": validation.first_name[2],
        "last_name_matched_against": validation.last_name[2],
        "season_start_date": None,
        "season_week_resolved": None,
        "estimated_refund_to_original": None,
        "estimated_store_credit": None,
        "transactions": transactions_wire(order),
        "currency_code": currency,
        "error": None,
    }


def run_both_ladders(
    season: SeasonDates,
    refundable: float,
    submitted_at: datetime,
) -> tuple[RefundResult, RefundResult]:
    est_original = estimate_refund_due(
        season, refundable, EstimateTierKind.REFUND_TO_ORIGINAL, submitted_at=submitted_at
    )
    est_credit = estimate_refund_due(
        season, refundable, EstimateTierKind.STORE_CREDIT, submitted_at=submitted_at
    )
    return est_original, est_credit
