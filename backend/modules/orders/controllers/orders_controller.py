"""FastAPI controller for the orders module.

Per design § 5.f (Stage 5):

  Owns ``DELETE /orders/{order_id}``. The route lives in its own
  ``APIRouter(prefix="/orders")`` rather than on the refunds router
  because FastAPI does not let one router emit a path under a different
  prefix.

D30 — there is NO orchestrator service. D31 — the cancel mutation is
invoked via ``shopify_client.run(schema.orders.mutations.cancel, **kwargs)``
directly from the call site. Property 7 (cancel without implicit refund)
is preserved because ``build_cancel_kwargs(...)`` does NOT include a
``refund_method`` key in the dict it returns.

Convention notes (D33 — Python 3.14+ style):
  - No ``from __future__ import annotations`` import.
  - ``X | None`` over the deprecated ``typing.Optional`` form.
  - Lowercase ``list[dict]`` / ``dict[str, Any]``.
"""

import os

from fastapi import APIRouter, Depends
from modules.refunds.inputs import build_cancel_kwargs
from pydantic import BaseModel, ConfigDict, Field
from shopify_client.shop_client import ShopifyClient, schema
from utils.shopify_refunds import ShopifyUserError

router = APIRouter(prefix="/orders", tags=["orders"])


def _shopify_client_dep() -> ShopifyClient:
    """FastAPI dependency that constructs a ``ShopifyClient`` from env.

    Mirrors the helper in ``refunds_controller`` — kept local rather
    than shared so each controller's dependency surface is self-contained
    and overridable independently in tests.
    """
    return ShopifyClient(
        store_id=os.environ["SHOPIFY__STORE_ID"],
        api_version=os.environ["SHOPIFY__API_VERSION"],
        token=os.environ["SHOPIFY__TOKEN__ADMIN"],
    )


class CancelOrderRequest(BaseModel):
    """Incoming body for ``DELETE /orders/{order_id}``.

    Pydantic because this is an incoming external request (D28).
    snake_case Python field names paired with camelCase aliases per the
    Stage 5 casing convention (D32).
    """

    model_config = ConfigDict(populate_by_name=True)

    approved_by: str = Field(..., alias="approvedBy")
    reason: str = "CUSTOMER"
    restock: bool = False
    notify_customer: bool = Field(False, alias="notifyCustomer")
    staff_note: str | None = Field(None, alias="staffNote")


@router.delete("/{order_id}")
async def cancel_order_route(
    order_id: str,
    body: CancelOrderRequest,
    shopify_client: ShopifyClient = Depends(_shopify_client_dep),
) -> dict:
    """Cancel a Shopify order.

    Pure cancel — no refund (Property 7). Builds the kwargs via
    ``build_cancel_kwargs(...)`` and invokes
    ``shopify_client.run(schema.orders.mutations.cancel, **cancel_kwargs)``
    directly. NO service-class wrapper, NO orchestrator.

    Returns a ``CancelOutcome``-shaped dict (``{jobId, jobDone}``) — the
    same shape used by ``POST /refunds/create``'s ``cancel`` block, so
    Slack-side renderers can reuse a single confirmation builder.
    Pre-D32, the keys are camelCase to match the wire format directly.
    """
    cancel_kwargs = build_cancel_kwargs(
        order_id=order_id,
        approved_by=body.approved_by,
        reason=body.reason,
        restock=body.restock,
        notify_customer=body.notify_customer,
    )
    payload = shopify_client.run(schema.orders.mutations.cancel, **cancel_kwargs)
    if payload.user_errors:
        raise ShopifyUserError("orderCancel", list(payload.user_errors))
    job = payload.to_dict().get("job") or {}
    return {
        "jobId": job.get("id", ""),
        "jobDone": bool(job.get("done", False)),
    }
