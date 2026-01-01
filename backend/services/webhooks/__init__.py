class WebhooksService:
    @staticmethod
    def verify_webhook_signature(request_body: bytes, hmac_header: str) -> bool:
        raise NotImplementedError("WebhooksService not yet implemented in new architecture")

