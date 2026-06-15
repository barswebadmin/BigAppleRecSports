"""Refund-request flow, independent of Lambda framing.

Input shape (``RefundRequest``) is the JSON the Google Sheets webhook posts.
Output shape (``RefundResponse``) is what we hand back — designed so the Slack
Deno app can render a "review this refund request" block from it without
further enrichment.

Side-effect-free: everything that talks to Shopify goes through ``shopify_client``;
all decision logic lives in pure validation / refund_calculator. The Lambda
entrypoint in ``main.py`` is the only thing that knows about AWS.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from functools import cache
from zoneinfo import ZoneInfo


# Naive form-submission timestamps are assumed to be in BARS's operational tz.
# This matters when the GAS form sends a display-string like "2026-03-11T00:30:00"
# (without a Z or offset) — interpreting it as UTC would shift the request by
# 4-5 hours and could land it in the wrong refund tier near the boundary day.
_BARS_TZ = ZoneInfo("America/New_York")

from pydantic import BaseModel, ConfigDict, Field

from registrations.refund_calculator import (
    EstimateTierKind,
    RefundResult,
    SeasonDates,
    estimate_refund_due,
    timing_label,
)
from shopify_client import ShopifyClient

from program_extractor import extract_program
from season_resolver import resolve_season_dates
from validation import ValidationResult, validate_request_against_order

logger = logging.getLogger(__name__)


# --- Input contract (webhook payload) ----------------------------------------


class RefundRequest(BaseModel):
    """JSON payload POSTed by the Google Sheets refund-form webhook.

    Matches what ``google-apps-scripts/projects/process-refunds-exchanges/src/lambdaWebhook.js``
    sends, field-for-field. Permissive by design — empty / malformed strings
    don't 400; downstream validation surfaces them as warnings on the response
    instead, so a Slack reviewer can see exactly what the form submitted vs.
    what's on the Shopify order.

    ``created_at`` is the form-submission timestamp (TZ-aware UTC when GAS uses
    ``Date.prototype.toISOString()``). The lambda uses it as the
    "submitted_at" for refund-tier resolution, so users get the tier they
    qualified for at submission time even if the lambda runs later.
    """

    model_config = ConfigDict(
        # Auto-strip whitespace on every string field. GAS already calls
        # ``.trim()`` on email, but not on every field; doing it here matches
        # the trim defensively across the board.
        str_strip_whitespace=True,
    )

    order_number: str = Field(
        default="",
        description="Order display name from the form. With or without leading '#' — "
        "``get_order_by_name`` normalizes either form. Empty → order_not_found in response.",
    )
    # Intentionally plain ``str`` (not ``EmailStr``). GAS can send an empty or
    # malformed email if the form field is blank or the form changed; we want
    # those to surface as a warning in the response, not a hard 400.
    email_address: str = Field(default="")
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    refund_or_credit: str = Field(
        default="credit",
        description='"refund" (to original payment) or "credit" (store credit). '
        "Anything other than refund-like → store credit (the safer / cheaper default).",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Form submission timestamp (ISO 8601 with Z, or null). "
        "Naïve datetimes are treated as America/New_York; missing → lambda invocation time.",
    )
    notes: str | None = None


# --- Output contract ---------------------------------------------------------


@dataclass
class RefundResponse:
    """Matches the Slack Deno app's ``RefundEvaluationPayload`` TS interface
    field-for-field. Same JSON is returned to the HTTP caller (GAS) AND
    POSTed to the Slack endpoint, so the Deno side has a single contract.

    Fields are grouped by source: echoed request inputs, lookup result,
    program context (sport/day/division), validation outcome, refund estimates.
    """

    # ── echoed from the request (so Slack can render the form values) ──
    email_address: str
    first_name: str
    last_name: str
    refund_or_credit: str

    # ── lookup result ──────────────────────────────────────────────────
    order_number: str
    order_id: str | None
    order_found: bool

    # ── validation outcome (soft — never blocks the response) ──────────
    validation_passed: bool
    warnings: list[str]

    # Defaulted fields (Slack interface has them optional or nullable).
    #
    # ``isTest`` is True for now — the Slack Deno workflow uses this to route
    # the message into the test path (skip user notifications, distinct channel,
    # etc.). Flip to False ONLY when the end-to-end flow has been validated and
    # we want refunds to fire for real. Keep this comment when flipping so
    # nobody loses the history of why it was True.
    isTest: bool = True
    notes: str | None = None

    # Program context (parsed from the order's first line item's product).
    sport: str | None = None
    day: str | None = None
    division: str | None = None

    # Product identity (order's first line item's product). product_id is the
    # Shopify GID; the Slack app builds the admin product URL from it.
    product_id: str | None = None
    product_title: str | None = None

    # Refund-timing diagnostics (so Slack can show *why* an estimate is what it
    # is). season_start_date is what we parsed from the product description (null
    # if unparseable). season_week_resolved is where the submission landed in the
    # week ladder, e.g. "after the start of week 5".
    season_start_date: str | None = None
    season_week_resolved: str | None = None

    # Order money facts.
    order_total: float | None = None
    total_refunded: float | None = None
    refundable_balance: float | None = None
    is_cancelled: bool | None = None

    # Match diagnostics (which order field the request value matched against).
    email_matched_against: str | None = None
    first_name_matched_against: str | None = None
    last_name_matched_against: str | None = None

    # Both ladders, so reviewers can compare.
    estimated_refund_to_original: dict | None = None
    estimated_store_credit: dict | None = None

    error: str | None = None

    def to_json(self) -> dict:
        return asdict(self)


# --- Client (cached at module load) ------------------------------------------


@cache
def _client() -> ShopifyClient:
    """One ShopifyClient per warm container. Reads creds from env at first use."""
    return ShopifyClient(
        api_token=os.environ["SHOPIFY__TOKEN__ADMIN"],
        api_version=os.environ["SHOPIFY__API_VERSION"],
        store_id=os.environ["SHOPIFY__STORE_ID"],
        location_id=os.environ.get("SHOPIFY__LOCATION_ID", ""),
    )


# --- Flow --------------------------------------------------------------------


def _tier_kind(refund_or_credit: str) -> EstimateTierKind:
    """Map the wire string to our enum. Unknown values default to store credit
    (the more conservative ladder — refund-to-original adds the 5% processing fee)."""
    return (
        EstimateTierKind.REFUND_TO_ORIGINAL
        if refund_or_credit.strip().lower() in ("refund", "refund_to_original", "original")
        else EstimateTierKind.STORE_CREDIT
    )


def _money(amount_str: str | None) -> float:
    return float(Decimal(amount_str)) if amount_str else 0.0


def _resolve_submitted_at(raw: datetime | None) -> datetime:
    """Coerce the form's submission timestamp into a TZ-aware datetime.

    The refund calculator's ``ensure_utc`` assumes naive datetimes are UTC, but
    a naive ISO string from GAS (e.g. ``"2026-03-11T00:30:00"``) is almost
    certainly NY-local — interpreting it as UTC would shift submissions by 4-5h
    and could mis-tier requests submitted near a boundary day.

    Aware datetimes pass through unchanged. ``None`` defaults to ``now`` in
    UTC.
    """
    if raw is None:
        return datetime.now(timezone.utc)
    if raw.tzinfo is None:
        return raw.replace(tzinfo=_BARS_TZ)
    return raw


def _resolve_week_label(season: SeasonDates, submitted_at: datetime) -> str | None:
    """Human label for where ``submitted_at`` lands in the season's week ladder,
    or ``None`` when the season start couldn't be parsed from the product."""
    if not season.start_date:
        return None
    return timing_label(season.to_schedule().week_index(submitted_at))


def _estimate_payload(result: RefundResult) -> dict:
    """Compact serialization of a RefundResult for the response."""
    return {
        "success": result.success,
        "amount": result.amount,
        "percentage": result.percentage,
        "penalty": result.penalty,
        "timing": result.timing,
        "has_processing_fee": result.has_processing_fee,
        "no_payment": result.no_payment,
        "message": result.message,
    }


def _echo_fields(req: RefundRequest) -> dict:
    """The five request-echo fields every response carries — kept in one place
    so adding a new echo field doesn't require touching every early-return."""
    return {
        "email_address": req.email_address,
        "first_name": req.first_name,
        "last_name": req.last_name,
        "refund_or_credit": req.refund_or_credit,
        "notes": req.notes,
    }


def handle_refund_request(req: RefundRequest) -> RefundResponse:
    """End-to-end: fetch order, validate identity, compute both estimates, respond.

    Builds a ``RefundResponse`` that matches the Slack Deno app's
    ``RefundEvaluationPayload`` interface. The caller (lambda_handler) is
    responsible for separately posting the same payload to the Slack
    endpoint via ``maybe_post_to_slack``.
    """
    if not req.order_number:
        return RefundResponse(
            **_echo_fields(req),
            order_number="",
            order_id=None,
            order_found=False,
            validation_passed=False,
            warnings=["Order number was empty in the request"],
            error="order_number_missing",
        )

    order = _client().get_order_by_name(name=req.order_number)
    if order is None:
        return RefundResponse(
            **_echo_fields(req),
            order_number=req.order_number,
            order_id=None,
            order_found=False,
            validation_passed=False,
            warnings=[f"No order found with name '{req.order_number}'"],
            error="order_not_found",
        )

    validation: ValidationResult = validate_request_against_order(
        request_email=str(req.email_address),
        request_first_name=req.first_name,
        request_last_name=req.last_name,
        order=order,
    )

    # Money facts
    order_total = _money(order.total_price_set.shop_money.amount if order.total_price_set else None)
    total_refunded = sum(
        (_money(r.total_refunded_set.shop_money.amount) for r in order.refunds if r.total_refunded_set),
        0.0,
    )
    refundable = max(0.0, order_total - total_refunded)

    # Season dates from the first line item's product (resolution source is
    # swappable — see season_resolver). Falls back to all-None when unavailable.
    first_item = order.line_items.nodes[0] if order.line_items.nodes else None
    product = first_item.product if first_item else None
    season = resolve_season_dates(product)
    submitted_at = _resolve_submitted_at(req.created_at)

    # Where did the submission land in the week ladder? Computed independently of
    # the tier so we can report it even when the result is a 0% (past-window) tier.
    season_week_resolved = _resolve_week_label(season, submitted_at)

    est_original = estimate_refund_due(
        season=season,
        total_paid=refundable,
        tier_kind=EstimateTierKind.REFUND_TO_ORIGINAL,
        submitted_at=submitted_at,
    )
    est_credit = estimate_refund_due(
        season=season,
        total_paid=refundable,
        tier_kind=EstimateTierKind.STORE_CREDIT,
        submitted_at=submitted_at,
    )

    # Surface partial-refund state as a warning, not a block (per policy spec).
    warnings = list(validation.warnings)
    if total_refunded > 0 and refundable > 0:
        warnings.append(
            f"Order has been partially refunded: ${total_refunded:.2f} of ${order_total:.2f}"
        )
    if refundable <= 0 and order_total > 0:
        warnings.append("Order has already been fully refunded")
    if order.cancelled_at is not None:
        warnings.append(f"Order was cancelled at {order.cancelled_at.isoformat()}")

    sport, day, division = extract_program(product)

    return RefundResponse(
        **_echo_fields(req),
        order_number=order.name,
        order_id=order.id,
        order_found=True,
        validation_passed=validation.all_passed,
        warnings=warnings,
        sport=sport,
        day=day,
        division=division,
        product_id=product.id if product else None,
        product_title=product.title if product else None,
        season_start_date=season.start_date,
        season_week_resolved=season_week_resolved,
        email_matched_against=validation.email.matched_against,
        first_name_matched_against=validation.first_name.matched_against,
        last_name_matched_against=validation.last_name.matched_against,
        estimated_refund_to_original=_estimate_payload(est_original),
        estimated_store_credit=_estimate_payload(est_credit),
        order_total=order_total,
        total_refunded=total_refunded,
        refundable_balance=refundable,
        is_cancelled=order.cancelled_at is not None,
    )
