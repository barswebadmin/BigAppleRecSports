"""FastAPI controller for the refunds module.

Per design § 2.e (Stage 2) and § 5.d / § 5.k.1 (Stage 5):

  Owns ``POST /refunds/validate`` (Stage 2) and ``POST /refunds/create``
  (Stage 5). Other routes (``PATCH /refunds/update``, ``POST /refunds/approve``,
  ``POST /refunds/deny``, ``DELETE /refunds/{id}``) remain placeholder 204s
  for shape stability.

D28 — outgoing responses are plain ``dict`` (NOT Pydantic). The estimate
authority builds the ``RefundRequestEval`` dict and the controller passes
it through with no further translation (after ``to_camel(...)`` at the
boundary, per D32 — Stage 6 wires this when the snake_case migration
lands).

D30 — there is NO orchestrator service. D31 — every Shopify mutation is
invoked via ``shopify_client.run(schema.<resource>.<mutations|queries>.<name>, **kwargs)``
directly from the call site. No service-class wrapper (the Stage 3
``ShopifyRefundService`` was deleted in Stage 5 § 5.k.0); the
cancel-then-refund branching in ``create_refund`` is trivial if/else,
each branch invoking one ``client.run(...)`` call.
"""

import os
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Response
from modules.refunds.inputs import build_cancel_kwargs, build_refund_kwargs
from modules.refunds.models.create_request import CreateRefundRequest
from modules.refunds.models.create_response import (
    CancelOutcome,
    CreateRefundResponse,
    RefundOutcome,
)
from modules.refunds.models.refund_request import RefundRequest
from modules.refunds.services.estimate_service import EstimateService
from shopify_client.shop_client import ShopifyClient, schema
from utils.shopify_refunds import ShopifyUserError

router = APIRouter(prefix="/refunds", tags=["refunds"])


def _shopify_client_dep() -> ShopifyClient:
    """FastAPI dependency that constructs a ``ShopifyClient`` from env.

    Not a one-line factory wrapper (banned per § 5.k.1) — this function
    does meaningful work (reading three env vars and threading them as
    keyword arguments to a constructor that requires them). It exists
    because ``ShopifyClient.__init__`` requires keyword args (``store_id``,
    ``api_version``, ``token``), so ``Depends(ShopifyClient)`` cannot be
    used directly the way ``Depends(EstimateService)`` is.

    Tests override it the standard FastAPI way:
    ``app.dependency_overrides[_shopify_client_dep] = lambda: FakeShopifyClient()``.
    """
    return ShopifyClient(
        store_id=os.environ["SHOPIFY__STORE_ID"],
        api_version=os.environ["SHOPIFY__API_VERSION"],
        token=os.environ["SHOPIFY__TOKEN__ADMIN"],
    )


@router.post("/validate")
async def validate_refund(
    body: RefundRequest,
    service: EstimateService = Depends(EstimateService),
) -> dict:
    """Compute both refund ladders + product/order metadata for the order
    referenced by ``body.order_number``.

    Response shape: ``RefundRequestEval`` (a TypedDict — see
    ``modules.refunds.models.estimate``). Returned as a plain ``dict``
    per D28; FastAPI does not validate the outgoing payload against any
    Pydantic model.
    """
    submitted_at = datetime.now(timezone.utc)
    return await service.compute_estimate(
        body.to_estimate_request(submitted_at=submitted_at),
    )


@router.post("/create")
async def create_refund(
    body: CreateRefundRequest,
    shopify_client: ShopifyClient = Depends(_shopify_client_dep),
) -> dict:
    """Cancel-then-refund execution.

    NO orchestrator service (D30). NO ``ShopifyRefundService`` class —
    the controller calls ``shopify_client.run(...)`` directly for each
    mutation (user directive: "ensure that orderCancel and refundCreate
    are not combined into a wrapper. call path should call them
    separately in the logic. no overloaded methods").

    Branching contract:
      - ``cancel=True, refund=False`` → cancel only (no refund mutation).
      - ``cancel=False, refund=True`` → refund only (no cancel mutation).
      - ``cancel=True, refund=True``  → cancel first, then refund. If the
        cancel raises, the refund is skipped and the error surfaces. If
        the refund raises after a successful cancel, the response includes
        ``cancel`` populated, ``refund=None``, and ``errors[]`` non-empty
        — partial-success state visible to the operator.
      - ``cancel=False, refund=False`` (or ``amount=None`` on refund) →
        no-op; returns ``{ok: True, cancel: None, refund: None, errors: []}``.

    Property 7 (cancel without implicit refund) is preserved because
    ``build_cancel_kwargs(...)`` does NOT include a ``refund_method`` key
    in the dict it returns; that key never reaches
    ``schema.orders.mutations.cancel``.
    """
    cancel_outcome: CancelOutcome | None = None
    refund_outcome: RefundOutcome | None = None
    errors: list[dict] = []

    try:
        if body.cancel:
            # Shopify's ``orderCancel`` mutation takes a single boolean
            # ``restock``; the richer ``restock_to`` lane (veteran /
            # early / general / waitlist) is consumed by the inventory
            # layer downstream — NOT by the cancel mutation itself.
            # Mapping: presence-of-``restock_to`` → ``restock=True``.
            # See § 5.e.
            cancel_kwargs = build_cancel_kwargs(
                order_id=body.order_id,
                approved_by=body.approved_by,
                restock=bool(body.restock_to),
                notify_customer=body.notify,
            )
            cancel_payload = shopify_client.run(
                schema.orders.mutations.cancel, **cancel_kwargs,
            )
            if cancel_payload.user_errors:
                raise ShopifyUserError(
                    "orderCancel", list(cancel_payload.user_errors),
                )
            cancel_outcome = _cancel_outcome_from_payload(
                cancel_payload.to_dict(),
            )

        if body.refund and body.amount is not None and body.amount > 0:
            # ``Decimal(str(...))`` round-trip preserves the exact decimal
            # representation Slack sent us (avoids 1.20 → 1.2 truncation
            # that bare ``Decimal(body.amount)`` would produce on a float).
            amount = Decimal(str(body.amount))

            # For original-payment refunds we need the order's
            # transactions list to derive the parent SALE/CAPTURE.
            # Re-fetch fresh from Shopify (D17 — the round-trip is small,
            # the re-fetch is intentional and cheap).
            transactions: list[dict] | None = None
            if body.refund_to == "original_method":
                order = shopify_client.run(
                    schema.orders.queries.by_id, id=body.order_id,
                )
                transactions = (
                    list(order.transactions or []) if order else []
                )

            refund_kwargs = build_refund_kwargs(
                order_id=body.order_id,
                amount=amount,
                refund_to=body.refund_to,
                notify=body.notify,
                transactions=transactions,
            )
            refund_payload = shopify_client.run(
                schema.refunds.mutations.create, **refund_kwargs,
            )
            if refund_payload.user_errors:
                raise ShopifyUserError(
                    "refundCreate", list(refund_payload.user_errors),
                )
            refund_outcome = _refund_outcome_from_payload(
                refund_payload.to_dict(), refund_to=body.refund_to,
            )
    except ShopifyUserError as exc:
        # The exception handler registered in main.py (Stage 3 § 3.e)
        # ALSO catches ``ShopifyUserError`` and maps to 422 — but we
        # catch locally here so a partial-success cancel-then-refund
        # (cancel succeeded, refund failed) is still surfaced with both
        # outcomes. The local except never escapes to the global
        # handler; the response carries ``errors[]`` populated and
        # ``ok=False``.
        errors = exc.errors

    response: CreateRefundResponse = {
        "ok": not errors,
        "cancel": cancel_outcome,
        "refund": refund_outcome,
        "errors": errors,
    }
    return response


def _cancel_outcome_from_payload(payload: dict) -> CancelOutcome:
    """Map Shopify's ``OrderCancelPayload`` dict → ``CancelOutcome`` shape.

    Keys are camelCase to match the existing ``models/estimate.py`` and
    the wire format (D32 snake_case migration is owned by Stage 6).
    """
    job = payload.get("job") or {}
    return {
        "jobId": job.get("id", ""),
        "jobDone": bool(job.get("done", False)),
    }


def _refund_outcome_from_payload(payload: dict, *, refund_to: str) -> RefundOutcome:
    """Map Shopify's ``RefundCreatePayload`` dict → ``RefundOutcome`` shape.

    For the store-credit branch the ``currency`` field is set to
    ``"STORE_CREDIT"`` so downstream consumers can distinguish it from
    the original-payment branch without re-inspecting the request body.
    """
    refund = payload.get("refund") or {}
    total = (refund.get("total_refunded_set") or {}).get("shop_money") or {}
    currency = (
        "STORE_CREDIT"
        if refund_to == "store_credit"
        else (total.get("currency_code") or "USD")
    )
    return {
        "refundId": refund.get("id", ""),
        "amount": float(total.get("amount") or 0.0),
        "currency": currency,
        "createdAt": refund.get("created_at", ""),
    }


# ── Placeholders for Stages 6/7 ─────────────────────────────────────────────
#
# These keep the router's URL surface stable (so any tooling that walks the
# OpenAPI schema sees the same shape later stages will fill in) without
# committing to behavior. Each returns 204 No Content.


@router.patch("/update")
async def update_refund_request_placeholder() -> Response:
    """Placeholder for ``PATCH /refunds/update`` (Stages 6/7)."""
    return Response(status_code=204)


@router.post("/approve")
async def approve_refund_request_placeholder() -> Response:
    """Placeholder for ``POST /refunds/approve`` (Stages 6/7)."""
    return Response(status_code=204)


@router.post("/deny")
async def deny_refund_request_placeholder() -> Response:
    """Placeholder for ``POST /refunds/deny`` (Stages 6/7)."""
    return Response(status_code=204)


@router.delete("/{refund_id}")
async def cancel_refund_request_placeholder(refund_id: str) -> Response:
    """Placeholder for ``DELETE /refunds/{refund_id}`` (Stages 6/7)."""
    return Response(status_code=204)
