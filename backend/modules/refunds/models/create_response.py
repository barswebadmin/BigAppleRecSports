"""Outgoing response shape for ``POST /refunds/create``.

Per design § 5.c (D28): plain ``TypedDict`` — NOT Pydantic. The controller
constructs the dict manually and FastAPI returns it directly.

Wire JSON is camelCase (idiomatic Slack/TS). Pending the Stage 6
casing-convention cleanup (D32 — snake_case Python keys + ``to_camel``
boundary helper), the TypedDict keys here are camelCase to match the
existing ``models/estimate.py`` (which is also pre-D32) and the wire
format. Stage 6 owns the snake_case migration across both modules in
lockstep with the ``utils/casing.py`` helper.

Convention notes (D33 — Python 3.14+ style):
  - No ``from __future__ import annotations`` import.
  - ``X | None`` over the deprecated ``typing.Optional`` form.
  - Lowercase ``list[dict]`` (no deprecated ``typing.List`` / ``typing.Dict`` forms).
"""

from typing import TypedDict


class CancelOutcome(TypedDict):
    """Payload returned when ``body.cancel`` was True and the cancel
    succeeded. Mirrors ``OrderCancelPayload.job`` from Shopify.

    Fields:
      - ``jobId``    Shopify async-job GID (cancel runs through a Job).
      - ``jobDone``  True when the cancel completed synchronously
                     (rare); False when it's still running on Shopify's
                     side (operator can poll).
    """

    jobId: str
    jobDone: bool


class RefundOutcome(TypedDict):
    """Payload returned when ``body.refund`` was True and the refund
    succeeded. Mirrors ``RefundCreatePayload.refund.{id, …}``.

    Fields:
      - ``refundId``   Shopify refund GID.
      - ``amount``     Refund amount in dollars (mirrors
                       ``refund.total_refunded_set.shop_money.amount``).
      - ``currency``   ISO currency code, OR the literal string
                       ``"STORE_CREDIT"`` for the store-credit branch
                       (so downstream consumers can distinguish without
                       re-inspecting the request body).
      - ``createdAt``  ISO 8601 UTC timestamp from Shopify.
    """

    refundId: str
    amount: float
    currency: str
    createdAt: str


class CreateRefundResponse(TypedDict, total=False):
    """The full ``/refunds/create`` response.

    ``total=False`` because partial-success states are valid:
      - cancel-only success: ``cancel`` populated, ``refund`` is ``None``.
      - refund-only success: ``refund`` populated, ``cancel`` is ``None``.
      - cancel succeeded + refund failed: ``cancel`` populated,
        ``refund`` is ``None``, ``errors[]`` non-empty (the controller's
        local try/except surfaces this state instead of letting the
        global handler swallow the cancel-succeeded outcome).

    The ``errors`` list carries Shopify user-error dicts (``{field,
    message, code?}``) — left as ``list[dict]`` because the wire shape
    matches Shopify's own ``UserError`` GraphQL type 1:1.
    """

    ok: bool
    cancel: CancelOutcome | None
    refund: RefundOutcome | None
    errors: list[dict]
