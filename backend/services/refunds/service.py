import os
from datetime import datetime
from typing import Any

import httpx
from box import Box
from lib.domain.registrations.refunds import (
    EstimateTierKind,
    RefundResult,
    SeasonDates,
    estimate_refund_due,
)
from shopify_client.shop_client import ShopifyClient, schema

from services.refunds.evaluation import (
    build_found_payload,
    build_not_found_payload,
    build_parse_error_payload,
    order_refund_facts,
    run_both_ladders,
)
from services.refunds.matching import validate_against_order
from services.refunds.requests import (
    CreateRefundRequest,
    EstimateRefundRequest,
    Ladder,
    RefundEstimate,
    RefundEstimateTier,
    RefundExecuteRequest,
    RefundRequestSubmission,
    RefundSubmitRequest,
)
from shared.exceptions import NotFoundError, UnprocessableError

client = ShopifyClient(
    store_id=os.environ.get("SHOPIFY__STORE_ID", ""),
    api_version=os.environ.get("SHOPIFY__API_VERSION", "2026-07"),
    token=os.environ.get("SHOPIFY__TOKEN__ADMIN", ""),
)

LADDER_TIER_KIND: dict[Ladder, EstimateTierKind] = {
    "refund_to_original": EstimateTierKind.REFUND_TO_ORIGINAL,
    "store_credit": EstimateTierKind.STORE_CREDIT,
}


def fetch_order(req: EstimateRefundRequest) -> Box:
    """Fetch a single order with full refund detail (line_items +
    custom_attributes + customer + refunds + transactions). For number-based
    lookups, resolves the GID via `by_name` first. Raises NotFoundError when no
    order matches."""
    if req.id:
        gid = req.id
    else:
        matches = client.run(schema.orders.queries.by_name, name=f"#{req.number}")
        if not matches:
            raise NotFoundError(f"Order not found: number={req.number}")
        gid = matches[0].id
    order = client.run(schema.orders.queries.by_id, id=gid)
    if order is None:
        raise NotFoundError(f"Order not found: id={gid}")
    return order


def tier_estimate(
    season: SeasonDates,
    order_total: float,
    tier_kind: EstimateTierKind,
    submitted_at: datetime | None,
) -> RefundEstimateTier | None:
    """Run one ladder. Returns None when the season can't produce a result."""
    result: RefundResult = estimate_refund_due(season, order_total, tier_kind, submitted_at=submitted_at)
    if not result.success:
        return None
    return RefundEstimateTier(
        amount=result.amount,
        percentage=result.percentage,
        penalty=result.penalty,
        message=result.message,
    )


async def estimate(req: EstimateRefundRequest) -> RefundEstimate:
    """Estimate refund + store-credit ladders for an order."""
    order = fetch_order(req)
    order_total = (
        float(order.total_price_set.shop_money.amount) if order.total_price_set and order.total_price_set.shop_money else 0.0
    )
    currency = (
        order.total_price_set.shop_money.currency_code
        if order.total_price_set and order.total_price_set.shop_money
        else None
    )

    product_html: str | None = None
    if order.line_items and order.line_items[0].product is not None:
        product_html = order.line_items[0].product.description_html

    if not product_html:
        return RefundEstimate(
            order_id=order.id,
            order_name=order.name,
            order_total=order_total,
            currency=currency,
            note="Product description HTML missing — cannot derive season dates.",
        )

    season = SeasonDates.from_html(product_html)
    if not season.start_date:
        return RefundEstimate(
            order_id=order.id,
            order_name=order.name,
            order_total=order_total,
            currency=currency,
            note="Season dates could not be parsed from product description.",
        )

    if req.total_weeks is not None:
        season = season.model_copy(update={"total_weeks": req.total_weeks})

    tiers = {
        ladder: tier_estimate(season, order_total, kind, req.submitted_at)
        for ladder, kind in LADDER_TIER_KIND.items()
    }

    return RefundEstimate(
        order_id=order.id,
        order_name=order.name,
        order_total=order_total,
        currency=currency,
        refund_to_original=tiers["refund_to_original"],
        store_credit=tiers["store_credit"],
    )


def _parent_capture_txn(transactions: list[dict]) -> dict | None:
    for txn in transactions:
        kind = (txn.get("kind") or "").upper()
        status = (txn.get("status") or "").upper()
        if kind in {"CAPTURE", "SALE"} and status == "SUCCESS":
            return txn
    return None


def _build_refund_transactions_for_shopify(
    order_id: str,
    amount: float,
    transactions: list[dict],
) -> list[dict]:
    cap = _parent_capture_txn(transactions)
    if not cap:
        raise UnprocessableError("No successful SALE/CAPTURE transaction found for refund to original payment")
    gateway = cap.get("gateway") or "shopify_payments"
    parent = cap.get("parent_id")
    parent_id = parent if parent else cap.get("id")
    if not parent_id:
        raise UnprocessableError("Could not determine parent transaction id for refund")
    return [
        {
            "order_id": order_id,
            "parent_id": parent_id,
            "amount": f"{amount:.2f}",
            "kind": "REFUND",
            "gateway": gateway,
        }
    ]


def _build_store_credit_refund_methods(amount: float, currency: str) -> list[dict]:
    return [
        {
            "storeCreditRefund": {
                "amount": {"amount": f"{amount:.2f}", "currencyCode": currency},
            }
        }
    ]


async def execute_refund_create(body: RefundExecuteRequest) -> dict[str, Any]:
    """Cancel the order when requested, then create a refund if amount > 0."""
    out: dict[str, Any] = {"cancel": None, "refund": None}
    idem = body.idempotency_key

    if body.cancel_order:
        cancel_key = f"{idem}:cancel" if idem else None
        cancel_payload = client.run(
            schema.orders.mutations.cancel,
            order_id=body.order_id,
            reason="CUSTOMER",
            restock=False,
            notify_customer=False,
            staff_note=f"Slack-approved cancel (by {body.approved_by})",
            idempotency_key=cancel_key,
        )
        if cancel_payload.user_errors:
            raise UnprocessableError(f"Order cancel failed: {list(cancel_payload.user_errors)}")
        out["cancel"] = cancel_payload.to_dict()

    if body.amount <= 0:
        return out

    currency = (body.currency or "USD").upper()
    note = body.note or f"Refund approved via Slack ({body.approved_by})"

    if body.refund_to == "store_credit":
        create_body = CreateRefundRequest(
            order_id=body.order_id,
            currency=currency,
            note=note,
            notify=body.notify,
            refund_methods=_build_store_credit_refund_methods(body.amount, currency),
        )
    else:
        txns = _build_refund_transactions_for_shopify(body.order_id, body.amount, body.transactions)
        create_body = CreateRefundRequest(
            order_id=body.order_id,
            currency=currency,
            note=note,
            notify=body.notify,
            transactions=txns,
        )

    refund_key = f"{idem}:refund" if idem else None
    refund_payload = client.run(
        schema.refunds.mutations.create,
        idempotency_key=refund_key,
        **create_body.model_dump(exclude_none=True),
    )
    if refund_payload.user_errors:
        raise UnprocessableError(f"Refund create failed: {list(refund_payload.user_errors)}")
    out["refund"] = refund_payload.to_dict()
    return out


async def create(body: CreateRefundRequest) -> dict[str, Any]:
    """Create a Shopify refund (low-level). Raises UnprocessableError on user_errors."""
    payload = client.run(
        schema.refunds.mutations.create,
        **body.model_dump(exclude_none=True),
    )
    if payload.user_errors:
        raise UnprocessableError(f"Refund create failed: {list(payload.user_errors)}")
    return payload.to_dict()


async def _post_slack_evaluation(url: str | None, evaluation: dict[str, Any]) -> tuple[bool, int, str]:
    trigger = (url or os.environ.get("SLACK__REFUND_EVAL_TRIGGER_URL") or "").strip()
    if not trigger:
        raise UnprocessableError(
            "Slack refund evaluation URL is not configured (set SLACK__REFUND_EVAL_TRIGGER_URL "
            "or pass slack_trigger_url on the request)",
        )
    async with httpx.AsyncClient(timeout=60.0) as http:
        response = await http.post(trigger, json={"evaluation_json": json.dumps(evaluation, default=str)})
    return response.is_success, response.status_code, response.text


async def submit(body: RefundSubmitRequest) -> dict[str, Any]:
    """Estimate ladders from season math, build Slack evaluation payload, POST to
    the Deno webhook trigger (`evaluation_json`)."""
    req_est = body.to_estimate_refund_request()
    try:
        order = fetch_order(req_est)
    except NotFoundError:
        evaluation = build_not_found_payload(body, error="order_not_found")
        ok, status, text = await _post_slack_evaluation(body.slack_trigger_url, evaluation)
        return {
            "ok": True,
            "evaluation": evaluation,
            "slack_posted": ok,
            "slack_status": status,
            "slack_response_excerpt": text[:500],
        }

    validation = validate_against_order(
        order,
        email=str(body.email),
        first_name=body.first_name,
        last_name=body.last_name,
    )

    _, _, refundable, _ = order_refund_facts(order)

    product_html: str | None = None
    if order.line_items and order.line_items[0].product is not None:
        product_html = order.line_items[0].product.description_html

    if not product_html:
        evaluation = build_parse_error_payload(
            order,
            body,
            validation=validation,
            note="Product description HTML missing — cannot derive season dates.",
        )
        ok, status, text = await _post_slack_evaluation(body.slack_trigger_url, evaluation)
        return {
            "ok": True,
            "evaluation": evaluation,
            "slack_posted": ok,
            "slack_status": status,
            "slack_response_excerpt": text[:500],
        }

    season = SeasonDates.from_html(product_html)
    if not season.start_date:
        evaluation = build_parse_error_payload(
            order,
            body,
            validation=validation,
            note="Season dates could not be parsed from product description.",
        )
        ok, status, text = await _post_slack_evaluation(body.slack_trigger_url, evaluation)
        return {
            "ok": True,
            "evaluation": evaluation,
            "slack_posted": ok,
            "slack_status": status,
            "slack_response_excerpt": text[:500],
        }

    if body.total_weeks is not None:
        season = season.model_copy(update={"total_weeks": body.total_weeks})

    submitted_at = body.submitted_at
    assert submitted_at is not None
    est_original, est_credit = run_both_ladders(season, refundable, submitted_at)
    evaluation = build_found_payload(
        order,
        body,
        season=season,
        est_original=est_original,
        est_credit=est_credit,
        validation=validation,
    )
    ok, status, text = await _post_slack_evaluation(body.slack_trigger_url, evaluation)
    return {
        "ok": True,
        "evaluation": evaluation,
        "slack_posted": ok,
        "slack_status": status,
        "slack_response_excerpt": text[:500],
    }


async def submit_request(body: RefundRequestSubmission) -> dict[str, Any]:
    """Accept a customer-submitted refund-request form."""
    return {
        "ok": True,
        "email": body.email,
        "order_number": body.order_number,
        "request_submitted_at": body.request_submitted_at.isoformat(),
    }


ACCEPTED_WEBHOOK_TOPICS = frozenset({"refunds/create"})


async def process_webhook(topic: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """Acknowledge a Shopify refunds webhook."""
    if topic not in ACCEPTED_WEBHOOK_TOPICS:
        raise UnprocessableError(f"Unsupported topic: {topic!r}")
    return {"ok": True, "topic": topic, "bytes": len(body)}
