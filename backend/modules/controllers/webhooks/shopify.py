import logging
from fastapi import HTTPException

from modules.integrations.shopify.client.shopify_security import ShopifySecurity


logger = logging.getLogger(__name__)


class ShopifyWebhooksController:
    def __init__(self, *, security: ShopifySecurity | None = None):
        self._security = security or ShopifySecurity()

    def handle_webhook_order_create(self, *, body: bytes, headers: dict[str, str]) -> bool:
        self._verify(body=body, headers=headers)
        return True

    def handle_webhook_refund_create(self, *, body: bytes, headers: dict[str, str]) -> bool:
        self._verify(body=body, headers=headers)
        return True

    def handle_webhook_product_update(self, *, body: bytes, headers: dict[str, str]) -> bool:
        self._verify(body=body, headers=headers)
        return True

    def handle_webhook_orders_update(self, *, body: bytes, headers: dict[str, str]) -> bool:
        self._verify(body=body, headers=headers)
        return True

    def handle_webhook_orders_cancel(self, *, body: bytes, headers: dict[str, str]) -> bool:
        self._verify(body=body, headers=headers)
        return True

    def _verify(self, *, body: bytes, headers: dict[str, str]) -> None:
        signature = headers.get("x-shopify-hmac-sha256", "")
        ok = self._security.verify_shopify_webhook(body, signature)
        if not ok:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

