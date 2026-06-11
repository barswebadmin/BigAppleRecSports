from __future__ import annotations

import logging
from datetime import date

from clients.shopify.models.base import ClientError
from clients.shopify.models.connections import OrderForRefund
from clients.shopify.models.shopify_order import ShopifyOrder
from clients.shopify.shopify_client import shopify_client

logger = logging.getLogger(__name__)


class OrdersService:
    def __init__(self) -> None:
        self.client = shopify_client

    async def get_orders_by_product_id(
        self,
        product_id: str | int | None,
        created_at_min: date | None = None,
        created_at_max: date | None = None,
    ) -> tuple[list[ShopifyOrder], list[ClientError]]:
        orders, errors = await self.client.get_orders(
            product_id=product_id,
            created_at_min=created_at_min,
            created_at_max=created_at_max,
        )
        logger.info("[OrdersService] %s orders returned", len(orders))
        return orders, errors

    async def get_order_for_refund(
        self,
        *,
        order_id: int | None = None,
        order_number: int | None = None,
    ) -> tuple[OrderForRefund | None, list[ClientError]]:
        if order_id is None and order_number is None:
            return None, [ClientError(message="order_id or order_number required")]

        if order_id is not None:
            return await self.client.get_order_for_refund(str(order_id))

        assert order_number is not None
        gid, errors = await self.client.resolve_order_gid_by_order_number(int(order_number))
        if errors:
            return None, errors
        if gid is None:
            return None, []
        return await self.client.get_order_for_refund(gid)

    async def get_order_details_for_refund_request(
        self,
        *,
        order_id: int | None = None,
        order_number: int | None = None,
    ) -> tuple[OrderForRefund | None, list[ClientError]]:
        return await self.get_order_for_refund(
            order_id=order_id,
            order_number=order_number,
        )
