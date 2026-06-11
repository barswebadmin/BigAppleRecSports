from __future__ import annotations

from clients.shopify.models.base import ClientError
from clients.shopify.models.shopify_order import ShopifyOrder
from models.orders import OrderRequest
from services.orders_service import OrdersService


class OrdersController:
    def __init__(self) -> None:
        self.service = OrdersService()

    async def get_orders(self, order_request: OrderRequest) -> tuple[list[ShopifyOrder], list[ClientError]]:
        return await self.service.get_orders_by_product_id(
            product_id=order_request.product_id,
            created_at_min=order_request.start_date,
            created_at_max=order_request.end_date,
        )

    async def update_order(self, order_id: str) -> dict:
        return {"order_id": order_id}

    async def delete_order(self, order_id: str) -> dict:
        return {"deleted": order_id}
