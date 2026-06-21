"""Estimate-side data models for the refund-cancel workflow.

Per design § 2.b (D28):

  - `EstimateRequest` is an INTERNAL Python value object built by the
    controller from the incoming `RefundRequest` body. Plain `@dataclass`
    — not a wire shape, doesn't cross the network boundary.

  - `TierEstimate`, `OrderInfo`, `ProductInfo`, `EstimateBlock`, and
    `RefundRequestEval` are all plain `TypedDict`s — NOT Pydantic models.
    They describe the OUTGOING wire shape served by `POST /refunds/validate`.
    The controller constructs the dict manually and FastAPI returns it
    directly.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, TypedDict

# ── Internal value object (not a wire shape) ────────────────────────────────


@dataclass
class EstimateRequest:
    """Inputs to the estimate authority.

    Internal value object — not a wire shape. The controller builds this from
    the incoming `RefundRequest` Pydantic model. It's a `@dataclass` because
    it doesn't cross the network boundary; using Pydantic here would buy
    nothing.
    """

    order_number: str
    """``"#48957"`` or ``"48957"`` — the controller normalizes via
    `utils.orders.strip_order_number_prefix` before/after this hop."""

    requested_refund_to: Literal["original_method", "store_credit"]

    submitted_at: datetime
    """When the request was filed (sheet timestamp). Must be timezone-aware;
    the controller defaults to ``datetime.now(timezone.utc)`` when the wire
    body omits it."""

    order_id: str | None = None
    """Shopify order GID (preferred when known). When ``None``, the service
    looks the order up by ``order_number``."""

    product_id: str | None = None
    """Shopify product GID (optional; service derives if absent)."""

    season_start_date: date | None = None
    """Optional override that bypasses HTML parsing of the product description
    (operator-supplied diagnostic)."""

    notes: str | None = None
    """Operator-supplied notes (advisory only — not consumed by the
    estimator math; round-tripped for diagnostic logging)."""


# ── Wire-shape TypedDicts (NOT Pydantic; D28) ───────────────────────────────


class TierEstimate(TypedDict):
    """One ladder's worth of tier output.

    Embedded into `RefundRequestEval.estimate.original` and
    `RefundRequestEval.estimate.storeCredit`. Plain TypedDict.

    Field semantics:
      - ``amount``               post-percentage amount in dollars (USD).
      - ``percentage``           tier percentage (e.g. 95 for "95% after 0%
                                 penalty"). 0 when no tier matched.
      - ``tierLabel``            human-readable timing string (e.g.
                                 ``"before week 1 started"``).
      - ``appliedProcessingFee`` 0.0 for store_credit; 0.05 (5%) for
                                 refund-to-original on post-week-0 tiers.
      - ``notes``                free-form annotations
                                 (``"no_payment_made"``, ``"estimate_error"``).
    """

    amount: float
    percentage: int
    tierLabel: str
    appliedProcessingFee: float
    notes: list[str]


class OrderInfo(TypedDict):
    """Order-level fields on `RefundRequestEval.order`.

    Built by `EstimateService._build_order_info(order, total_paid)`.
    """

    id: str
    """Shopify order GID."""

    number: str
    """Shopify display name (e.g. ``"#48957"``)."""

    customerName: str
    email: str
    """The order's customer email — NOT the requester's email."""

    amountPaid: float
    """Total paid on the order, in dollars."""

    currency: str


class ProductInfo(TypedDict):
    """Product-level fields on `RefundRequestEval.product`.

    Built by `EstimateService._build_product_info(order, season)`. The
    extraction strategy lives in that service method:

      - ``id`` / ``url``       direct from ``line_items[0].product``.
      - ``year``, ``season``,
        ``sport``, ``day``,
        ``division``           parsed from the product title via
                               `utils.orders.parse_product_title`; falls
                               back to ``product.product_type`` /
                               ``product.tags`` when title parsing fails.
      - ``week1Start`` …       ISO-date strings derived from
        ``week5Start``         `SeasonDates.from_html(product.description_html)
                               .to_schedule().dates`. Absent or unparseable
                               weeks are ``None``.
    """

    id: str
    url: str
    year: int
    season: str
    sport: str
    day: str
    division: str
    week1Start: str | None
    week2Start: str | None
    week3Start: str | None
    week4Start: str | None
    week5Start: str | None


class EstimateBlock(TypedDict):
    """The ``estimate`` sub-object on `RefundRequestEval`. Both ladders are
    always populated — the Slack handler shows the operator both options."""

    original: TierEstimate
    storeCredit: TierEstimate


class RefundRequestEval(TypedDict, total=False):
    """OUTGOING wire shape for `POST /refunds/validate`.

    `total=False` lets `validationErrors` be omitted on the happy path;
    the required keys (``ok``, ``isValid``, ``order``, ``product``,
    ``estimate``) are always populated by the controller.

    Per D28, this is a plain TypedDict — NOT a Pydantic model. The Slack
    app reads field paths directly into its block builders.
    """

    ok: bool
    isValid: bool
    """Replaces the previous ``validation.matched`` field."""

    validationErrors: list[str] | None
    """Replaces ``validation.mismatches[]`` — flat ``list[str]`` only."""

    order: OrderInfo
    product: ProductInfo
    estimate: EstimateBlock
