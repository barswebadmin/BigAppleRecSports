"""Single estimate authority for the refund-cancel workflow.

Per design § 2.c (Stage 2):

  ``EstimateService.compute_estimate(req)`` wraps the pure-math tier resolver
  in ``backend/modules/refunds/refund_calculator.py`` with a Shopify-order
  lookup, a season-derivation step, and a dual-ladder evaluation. Every
  backend caller of refund-estimate logic (FastAPI controller, legacy
  callsites being migrated in Stage 2) goes through this service.

Stage 5 § 5.k.0 deletion: ``ShopifyRefundService`` is gone. The estimate
service now takes a ``shopify_client: ShopifyClient | None = None``
constructor argument and lazy-builds a client from env on first use. The
order-lookup helper that used to live on the service class
(``fetch_order_for_refund``) is inlined here as a private method calling
``client.run(schema.orders.queries.by_name, ...)`` /
``client.run(schema.orders.queries.by_id, ...)`` directly.

The service returns a fully-built ``RefundRequestEval`` dict — NOT a
Pydantic model (D28). The controller passes the dict back to FastAPI
verbatim (after ``to_camel(...)`` at the boundary, per D32).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal

from modules.refunds.models.estimate import (
    EstimateBlock,
    EstimateRequest,
    OrderInfo,
    ProductInfo,
    RefundRequestEval,
    TierEstimate,
)
from modules.refunds.refund_calculator import (
    EstimateTierKind,
    RefundResult,
    SeasonDates,
    estimate_refund_due,
)
from shopify_client.shop_client import ShopifyClient, schema
from utils.orders import parse_product_title

_REFUND_TO_KIND = {
    "original_method": EstimateTierKind.REFUND_TO_ORIGINAL,
    "store_credit": EstimateTierKind.STORE_CREDIT,
}


class EstimateService:
    """Single estimate authority for the refund-cancel workflow.

    Wraps the pure-math tier resolver in ``refund_calculator.py`` with a
    Shopify-order lookup + season derivation + dual-ladder evaluation.
    Returns a fully-built ``RefundRequestEval`` dict (NOT a Pydantic model;
    D28). The FastAPI controller returns the dict directly (with
    ``to_camel(...)`` at the boundary, per D32).
    """

    def __init__(self) -> None:
        # Stage 5 § 5.k.0 — ``ShopifyRefundService`` is gone. The lazy
        # ``.client`` property env-builds the canonical ``ShopifyClient``
        # on first access; tests inject a fake the FastAPI way via
        # ``app.dependency_overrides[EstimateService] = lambda: fake``
        # rather than via constructor injection (the parameter was
        # removed because FastAPI's ``Depends(EstimateService)`` cannot
        # introspect a typed ``ShopifyClient | None`` parameter as a
        # sub-dependency, which would crash route registration).
        self._shopify_client: ShopifyClient | None = None

    @property
    def client(self) -> ShopifyClient:
        """Lazy property — the canonical Shopify client is constructed
        from env on first access. Implemented as a property (rather than
        an eager module-level singleton) so unit tests that only exercise
        the pure private helpers (``_apply_tier``, ``_build_product_info``,
        ``parse_product_title``) never trigger the Shopify-client
        construction."""
        if self._shopify_client is None:
            import os

            self._shopify_client = ShopifyClient(
                store_id=os.environ["SHOPIFY__STORE_ID"],
                api_version=os.environ["SHOPIFY__API_VERSION"],
                token=os.environ["SHOPIFY__TOKEN__ADMIN"],
            )
        return self._shopify_client

    # ── Public API ──────────────────────────────────────────────────────────

    async def compute_estimate(self, req: EstimateRequest) -> RefundRequestEval:
        """Compute both refund ladders + product/order metadata for a single
        order, returning the wire-shaped ``RefundRequestEval`` dict.

        Preconditions:
          - ``req.order_number`` is a non-empty string (controller validates).
          - ``req.submitted_at`` is timezone-aware (controller defaults to
            ``datetime.now(timezone.utc)``).

        Postconditions:
          - Returns a ``RefundRequestEval`` dict (snake_case keys per D32)
            with ``ok``, ``is_valid``, ``order``, ``product``, and
            ``estimate`` populated. ``validation_errors`` is absent on the
            happy path; populated as a flat ``list[str]`` when
            ``is_valid`` is False.
          - Calls ``refund_calculator.estimate_refund_due`` exactly twice
            (once per ``EstimateTierKind``).
          - Issues at most one Shopify call (one ``by_id`` query, plus one
            ``by_name`` query when ``order_id`` is not provided).

        Raises:
          - ``ValueError`` when no order matches ``req.order_number``. The
            FastAPI exception handler in ``main.py`` translates this to an
            HTTP 404 (Stage 3 owns registering the handler).
        """
        order = self._fetch_order(
            order_id=req.order_id,
            order_number=req.order_number,
        )
        if order is None:
            # Until Stage 3 lands a dedicated `OrderNotFoundError`, raise a
            # plain ValueError that the global exception handler catches.
            # The controller never sees this directly.
            raise ValueError(
                f"Order not found: {req.order_number!r}",
            )

        season = self._resolve_season(order, override=req.season_start_date)
        total_paid = self._extract_total_paid(order)

        estimate: EstimateBlock = {
            "original": self._apply_tier(
                season, total_paid, "original_method", req.submitted_at
            ),
            "store_credit": self._apply_tier(
                season, total_paid, "store_credit", req.submitted_at
            ),
        }

        eval_dict: RefundRequestEval = {
            "ok": True,
            "is_valid": True,
            "order": self._build_order_info(order, total_paid),
            "product": self._build_product_info(order, season),
            "estimate": estimate,
        }
        return eval_dict

    # ── Private helpers ─────────────────────────────────────────────────────

    def _fetch_order(
        self,
        *,
        order_id: str | None = None,
        order_number: str | None = None,
    ) -> Any:
        """Fetch a single order with refund-grade detail directly via the
        canonical Shopify client (no service-class wrapper, per § 5.k.0).

        Preconditions:
          - Exactly one of ``order_id`` or ``order_number`` is non-None.
          - When ``order_number`` is provided, may include or omit the
            leading ``"#"``.

        Postconditions:
          - Returns a Box-wrapped order dict with snake_case keys, or
            ``None`` when no order matches ``order_number`` (id-based
            lookups raise).

        Raises:
          - ``ValueError`` when both id and number are missing.
          - The underlying gql/httpx exceptions on transport failure.
        """
        if not order_id and not order_number:
            raise ValueError("_fetch_order requires order_id or order_number")
        if order_id is None:
            assert order_number is not None
            name = order_number if order_number.startswith("#") else f"#{order_number}"
            matches = self.client.run(schema.orders.queries.by_name, name=name)
            if not matches:
                return None
            order_id = matches[0].id
        return self.client.run(schema.orders.queries.by_id, id=order_id)

    def _resolve_season(self, order: Any, *, override=None) -> SeasonDates:
        """Pick the season dates for ``order``, preferring an explicit
        override when given. Falls back to parsing the product-description
        HTML (which is what ``SeasonDates.from_html`` already does).

        Correctness properties:
          - When ``override`` is given, returns a `SeasonDates` whose
            ``start_date`` is ``M/D/YYYY`` of the override.
          - Returns an all-``None`` ``SeasonDates`` when the season cannot
            be derived; ``_apply_tier`` then routes to the
            "season-missing" branch via ``RefundResult.error()``.
        """
        if override is not None:
            return SeasonDates(start_date=f"{override.month}/{override.day}/{override.year}")

        line_items = _safe_get(order, "line_items") or []
        if not line_items:
            return SeasonDates()
        first = line_items[0]
        product = _safe_get(first, "product")
        product_html = _safe_get(product, "description_html") if product is not None else None
        if not product_html:
            return SeasonDates()
        return SeasonDates.from_html(product_html)

    def _apply_tier(
        self,
        season: SeasonDates,
        total_paid: Decimal,
        refund_to: Literal["original_method", "store_credit"],
        submitted_at: datetime,
    ) -> TierEstimate:
        """Run one ladder through the canonical estimator and translate
        the result into a wire-shape ``TierEstimate`` (TypedDict — NOT
        Pydantic; D28; snake_case keys per D32).

        Correctness properties:
          - Calls ``estimate_refund_due`` exactly once.
          - ``applied_processing_fee`` is ``0.05`` only for
            ``refund_to == "original_method"`` AND when the result has
            ``has_processing_fee=True``; otherwise ``0.0``.
          - ``notes`` includes ``"no_payment_made"`` when the order had
            zero total paid, ``"estimate_error"`` when the estimator
            could not compute a result.
          - ``tier_label`` is the canonical ``RefundResult.timing`` string
            (e.g. ``"before week 1 started"``).
        """
        tier_kind = _REFUND_TO_KIND[refund_to]
        result: RefundResult = estimate_refund_due(
            season,
            float(total_paid),
            tier_kind,
            submitted_at=submitted_at,
        )

        notes: list[str] = []
        if not result.success:
            notes.append("estimate_error")
        if result.no_payment:
            notes.append("no_payment_made")

        applied_fee = 0.05 if result.has_processing_fee else 0.0

        return {
            "amount": float(result.amount),
            "percentage": int(result.percentage),
            "tier_label": result.timing or "",
            "applied_processing_fee": applied_fee,
            "notes": notes,
        }

    def _build_order_info(self, order: Any, total_paid: Decimal) -> OrderInfo:
        """Build the ``order`` sub-object on ``RefundRequestEval``.

        Correctness properties (snake_case keys per D32):
          - ``id``         pulls ``order.id`` (the Shopify GID).
          - ``number``     pulls ``order.name`` (the ``"#48957"`` form).
          - ``email``      pulls ``order.email`` falling back to
                           ``order.customer.email``.
          - ``customer_name``  is ``"<first> <last>"`` derived from
                              ``order.customer`` when present, else the
                              ``order.billing_address`` name, else ``""``.
          - ``amount_paid``  is ``float(total_paid)``.
          - ``currency``    pulls
                            ``order.total_price_set.shop_money.currency_code``,
                            defaulting to ``"USD"``.
        """
        customer = _safe_get(order, "customer")
        first_name = _safe_get(customer, "first_name") or ""
        last_name = _safe_get(customer, "last_name") or ""
        full_name = f"{first_name} {last_name}".strip()
        if not full_name:
            billing = _safe_get(order, "billing_address")
            full_name = (_safe_get(billing, "name") or "").strip()

        email = (
            _safe_get(order, "email")
            or _safe_get(customer, "email")
            or ""
        )

        currency = (
            _safe_get(_safe_get(_safe_get(order, "total_price_set"), "shop_money"), "currency_code")
            or "USD"
        )

        return {
            "id": _safe_get(order, "id") or "",
            "number": _safe_get(order, "name") or "",
            "customer_name": full_name,
            "email": email,
            "amount_paid": float(total_paid),
            "currency": currency,
        }

    def _build_product_info(self, order: Any, season: SeasonDates) -> ProductInfo:
        """Build the ``product`` sub-object on ``RefundRequestEval``.

        Field-extraction strategy (per design § 2.c; snake_case keys per
        D32):
          - ``id``, ``url``           direct from
                                       ``line_items[0].product``.
          - ``year``, ``season``,
            ``sport``, ``day``,
            ``division``              parsed from product title via
                                       :func:`utils.orders.parse_product_title`,
                                       falling back to product attributes
                                       (``product_type``, ``tags``) when
                                       title parsing fails.
          - ``week1_start`` …
            ``week5_start``           derived from
                                       ``SeasonDates.from_html(...).to_schedule().dates``.
                                       Each is the ISO-date string of that
                                       week's session; absent or
                                       unparseable weeks resolve to
                                       ``None``.
        """
        line_items = _safe_get(order, "line_items") or []
        first = line_items[0] if line_items else None
        product = _safe_get(first, "product") if first is not None else None

        product_id = _safe_get(product, "id") or ""
        product_url = _safe_get(product, "online_store_url") or ""
        if not product_url:
            handle = _safe_get(product, "handle")
            if handle:
                product_url = f"https://bigapplerecsports.com/products/{handle}"

        title = _safe_get(product, "title") or ""
        parsed = parse_product_title(title)

        product_type = _safe_get(product, "product_type") or ""
        tags_raw = _safe_get(product, "tags")
        tags = _normalize_tags(tags_raw)

        # Year falls back to 0 when neither title nor tags carry one — the
        # downstream Slack render leaves it blank but the field is required
        # by ``ProductInfo``.
        year = parsed.get("year") or _year_from_tags(tags) or 0
        season_str = parsed.get("season") or _season_from_tags(tags) or ""
        sport = parsed.get("sport") or product_type or ""
        day = parsed.get("day") or _day_from_tags(tags) or ""
        division = parsed.get("division") or _division_from_tags(tags) or ""

        weeks = _week_starts_from_season(season)

        return {
            "id": product_id,
            "url": product_url,
            "year": int(year),
            "season": season_str,
            "sport": sport,
            "day": day,
            "division": division,
            "week1_start": weeks[0],
            "week2_start": weeks[1],
            "week3_start": weeks[2],
            "week4_start": weeks[3],
            "week5_start": weeks[4],
        }

    @staticmethod
    def _extract_total_paid(order: Any) -> Decimal:
        """Pull the order's total amount paid into a `Decimal`.

        Correctness properties:
          - Reads ``order.total_price_set.shop_money.amount`` (the
            schema-registry client's canonical path).
          - Returns ``Decimal("0")`` when the path is missing or unparseable
            — callers translate this to the "no payment was made" branch
            via ``RefundResult.no_payment_made()``.
        """
        try:
            shop_money = _safe_get(_safe_get(order, "total_price_set"), "shop_money")
            if shop_money is None:
                return Decimal("0")
            amount = _safe_get(shop_money, "amount")
            if amount is None or amount == "":
                return Decimal("0")
            return Decimal(str(amount))
        except Exception:  # noqa: BLE001 - defensive against unexpected shapes
            return Decimal("0")


# ── Module-private helpers ──────────────────────────────────────────────────


def _safe_get(obj: Any, key: str) -> Any:
    """Look up ``key`` on ``obj`` whether it's a Box / dict / dataclass /
    namespace. Returns ``None`` on miss. Used because the canonical Shopify
    client returns Box-wrapped dicts (snake_case attribute access), but
    tests and legacy callers may pass plain dicts.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _normalize_tags(tags: Any) -> list[str]:
    """Coerce Shopify tags (list[str] or comma-string) into ``list[str]``."""
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if t]
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    return []


def _year_from_tags(tags: list[str]) -> int | None:
    for tag in tags:
        if tag.isdigit() and len(tag) == 4 and tag.startswith("20"):
            return int(tag)
    return None


_SEASON_TAGS = {"Winter", "Spring", "Summer", "Fall"}
_DAY_TAGS = {
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}
_DIVISION_TAGS = {"WTNB+", "WTNB", "Open"}


def _season_from_tags(tags: list[str]) -> str | None:
    for tag in tags:
        if tag in _SEASON_TAGS:
            return tag
    return None


def _day_from_tags(tags: list[str]) -> str | None:
    for tag in tags:
        if tag in _DAY_TAGS:
            return tag
    return None


def _division_from_tags(tags: list[str]) -> str | None:
    for tag in tags:
        if tag in _DIVISION_TAGS:
            return tag
    return None


def _week_starts_from_season(
    season: SeasonDates,
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """Five ISO-date strings (or ``None``) for the first five tier-cutoffs
    after the synthetic 2-weeks-prior anchor.

    ``WeekSchedule.dates`` lays out the cutoffs as
    ``[anchor-2w, week1, week2, week3, week4, week5]`` — we drop the
    leading anchor and emit the next five (week 1 through week 5).
    """
    if not season.start_date:
        return (None, None, None, None, None)
    try:
        schedule = season.to_schedule()
    except Exception:  # noqa: BLE001 - season may have malformed start
        return (None, None, None, None, None)

    # `schedule.dates[0]` is the synthetic 2-weeks-prior anchor; the next
    # five are weeks 1–5 (UTC datetimes at 07:00).
    week_dates = schedule.dates[1:6]
    out: list[str | None] = []
    for i in range(5):
        if i < len(week_dates):
            out.append(_to_iso_date(week_dates[i]))
        else:
            out.append(None)
    # Guarantee a five-tuple regardless of `WeekSchedule` config.
    while len(out) < 5:
        out.append(None)
    return (out[0], out[1], out[2], out[3], out[4])


def _to_iso_date(dt: datetime) -> str:
    """Render a UTC-anchored cutoff datetime back to an ISO ``YYYY-MM-DD``
    date string (drops the time-of-day component)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Shift forward by 0 days; the schedule already anchors at 07:00 UTC.
    # The date in UTC is what BARS treats as the session date.
    return (dt + timedelta(days=0)).date().isoformat()
