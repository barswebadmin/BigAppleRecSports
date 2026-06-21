class WebhooksService:
    @staticmethod
    def verify_webhook_signature(request_body: bytes, hmac_header: str) -> bool:
        from modules.integrations.shopify.client.shopify_security import ShopifySecurity

        return ShopifySecurity().verify_shopify_webhook(request_body, hmac_header)

