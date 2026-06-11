from __future__ import annotations

from clients.shopify.models.shopify_order import ShopifyOrder

from models.api_base_model import ApiBaseModel
from models.types import (
    DayOfWeekEnum,
    DivisionEnum,
    EndDate,
    NormalizedInt,
    ProductHandle,
    SeasonEnum,
    SportEnum,
    StartDate,
    Year,
)


class OrderRequest(ApiBaseModel):
    """Canonical order filter payload (body, tests, services). No FastAPI ``Query`` here."""

    order_id: NormalizedInt | None = None
    order_number: NormalizedInt | None = None
    product_id: NormalizedInt | None = None
    handle: ProductHandle | None = None
    start_date: StartDate | None = None
    end_date: EndDate | None = None
    season: SeasonEnum | None = None
    year: Year | None = None
    sport: SportEnum | None = None
    day: DayOfWeekEnum | None = None
    division: DivisionEnum | None = None


class OrdersListResponse(ApiBaseModel):
    """JSON body for GET /orders/orders when orders exist."""

    orders: list[ShopifyOrder]
