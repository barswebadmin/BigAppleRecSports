"""Refund-domain input builders for Shopify mutations.

Module-level functions only — NO class. Each function takes the small set
of primitives the controller already has and returns a ``dict[str, Any]``
ready to splat into ``shopify_client.run(schema.x.y.z, **kwargs)``.

The transaction-side primitives are business-agnostic and live one level
out, in ``backend/utils/shopify_refunds.py``. These domain-aware functions
wrap those primitives with the refund-domain knowledge of
``refund_to == "original_method" | "store_credit"``.

Per Stage 5 § 5.d / § 5.k.0: NO ``ShopifyRefundService`` class wraps the
mutations. The controller's call site invokes
``shopify_client.run(schema.<resource>.<mutations|queries>.<name>, **kwargs)``
directly, splatting the dict returned here.
"""

from decimal import Decimal
from typing import Any, Literal

from utils.shopify_refunds import (
    build_refund_transactions_for_shopify,
    build_store_credit_refund_methods,
)


def build_cancel_kwargs(
    *,
    order_id: str,
    approved_by: str,
    restock: bool = False,
    notify_customer: bool = False,
    reason: str = "CUSTOMER",
) -> dict[str, Any]:
    """Build the ``**kwargs`` for ``client.run(schema.orders.mutations.cancel, ...)``.

    Does NOT include ``refund_method`` (Property 7 — cancel never
    implicitly refunds). The returned dict is splat directly into
    ``client.run(...)`` at the call site.

    Correctness properties:
      - ``staff_note`` is always populated (Shopify accepts an empty
        string but BARS audit trails benefit from the approver id).
      - ``reason`` defaults to ``"CUSTOMER"`` (the most common cancel
        reason for refund-flow cancels).
      - The output is always a flat ``dict[str, Any]`` with exactly five
        keys.
    """
    return {
        "order_id": order_id,
        "reason": reason,
        "restock": restock,
        "notify_customer": notify_customer,
        "staff_note": f"Slack-approved cancel (by {approved_by})",
    }


def build_refund_kwargs(
    *,
    order_id: str,
    amount: Decimal,
    refund_to: Literal["original_method", "store_credit"],
    currency: str = "USD",
    notify: bool = False,
    note: str | None = None,
    transactions: list[dict] | None = None,
) -> dict[str, Any]:
    """Build the ``**kwargs`` for ``client.run(schema.refunds.mutations.create, ...)``.

    Routes to the original-payment branch or the store-credit branch
    based on ``refund_to``. Both branches share the common kwargs
    (``order_id``, ``currency``, ``note``, ``notify``); the branch-specific
    field (``transactions=`` vs. ``refund_methods=``) is added by the
    business-agnostic helpers in ``utils.shopify_refunds``.

    Correctness properties:
      - When ``refund_to == "store_credit"``, the returned dict has a
        ``refund_methods`` key but NOT a ``transactions`` key.
      - When ``refund_to == "original_method"``, the returned dict has a
        ``transactions`` key but NOT a ``refund_methods`` key, and the
        caller MUST pass ``transactions`` (the order's existing
        transactions list).
      - Raises ``ValueError`` when ``refund_to == "original_method"`` and
        ``transactions`` is ``None``.
      - ``note`` defaults to a fixed Slack-workflow string when omitted.
    """
    note = note or "Refund approved via Slack workflow"
    common: dict[str, Any] = {
        "order_id": order_id,
        "currency": currency,
        "note": note,
        "notify": notify,
    }
    if refund_to == "store_credit":
        common["refund_methods"] = build_store_credit_refund_methods(amount, currency)
    else:  # original_method
        if transactions is None:
            raise ValueError(
                "build_refund_kwargs(refund_to='original_method') requires transactions list",
            )
        common["transactions"] = build_refund_transactions_for_shopify(
            order_id, amount, transactions,
        )
    return common
