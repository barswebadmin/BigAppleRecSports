"""Business-agnostic Shopify-refund primitives.

Module-level helpers that take and return primitives only (``list[dict]``,
``Decimal``, ``str``). They have NO domain knowledge of refund requests /
Slack approvals / estimate ladders. Tests exercise them as pure functions
with no Shopify client involved.

Lifted from the deleted
``backend/modules/refunds/services/shopify_refund_service.py`` (Stage 5
§ 5.k.0): the leading-underscore prefix is dropped (the helpers are now
part of this module's public API), and the ``@staticmethod`` indirection
goes away (they're plain module-level functions).

``ShopifyUserError`` also lives here so the canonical FastAPI exception
handler in ``backend/main.py`` (Stage 3 § 3.e) keeps its single import
point after the service-class teardown.
"""

from decimal import Decimal


class ShopifyUserError(Exception):
    """Raised when Shopify returns non-empty user_errors on a mutation.

    Mapped to HTTP 422 by the FastAPI exception handler in ``main.py``.
    """

    def __init__(self, mutation: str, errors: list[dict]) -> None:
        super().__init__(f"{mutation}: {errors}")
        self.mutation = mutation
        self.errors = errors


def parent_capture_txn(transactions: list[dict]) -> dict | None:
    """Return the first txn whose ``(kind, status)`` matches
    ``("CAPTURE"|"SALE", "SUCCESS")``, or ``None``.

    Correctness properties:
      - Empty input returns ``None``.
      - The match is case-insensitive on both ``kind`` and ``status``
        (Shopify's REST and GraphQL APIs disagree on casing).
      - The first match wins; iteration order is preserved.
    """
    for txn in transactions:
        kind = (txn.get("kind") or "").upper()
        status = (txn.get("status") or "").upper()
        if kind in {"CAPTURE", "SALE"} and status == "SUCCESS":
            return txn
    return None


def build_refund_transactions_for_shopify(
    order_id: str,
    amount: Decimal,
    transactions: list[dict],
) -> list[dict]:
    """Build ``[OrderTransactionInput!]`` for refund-to-original-payment.

    Raises ``ShopifyUserError("refundCreate", ...)`` when no eligible
    parent SALE/CAPTURE transaction is found.

    Correctness properties:
      - The returned list always has length 1 (Shopify accepts a single
        refund-transaction input per refundCreate).
      - ``amount`` is rendered with exactly two decimal places (Shopify's
        Money scalar).
      - ``parent_id`` falls back to the capture's own ``id`` when the
        capture has no explicit ``parent_id`` (the capture itself is the
        root payment).
      - ``gateway`` defaults to ``"shopify_payments"`` when the capture
        does not carry one (matches Shopify's own implicit default).
    """
    cap = parent_capture_txn(transactions)
    if not cap:
        raise ShopifyUserError(
            "refundCreate",
            [{"message": "No successful SALE/CAPTURE transaction found for refund to original payment"}],
        )
    gateway = cap.get("gateway") or "shopify_payments"
    parent = cap.get("parent_id")
    parent_id = parent if parent else cap.get("id")
    if not parent_id:
        raise ShopifyUserError(
            "refundCreate",
            [{"message": "Could not determine parent transaction id for refund"}],
        )
    return [
        {
            "order_id": order_id,
            "parent_id": parent_id,
            "amount": f"{Decimal(amount):.2f}",
            "kind": "REFUND",
            "gateway": gateway,
        }
    ]


def build_store_credit_refund_methods(amount: Decimal, currency: str) -> list[dict]:
    """Build ``[RefundMethodInput!]`` for the store-credit refund branch.

    Correctness properties:
      - The returned list always has length 1.
      - ``amount`` is rendered with exactly two decimal places.
      - ``currencyCode`` is forwarded as-is — callers pass the order's
        currency code (typically ``"USD"``).
    """
    return [
        {
            "storeCreditRefund": {
                "amount": {"amount": f"{Decimal(amount):.2f}", "currencyCode": currency},
            }
        }
    ]
