import os
from typing import Optional


class ShopifyConfig:
    def __init__(self, ENVIRONMENT: str):
        # Environment-specific Shopify configuration
        if ENVIRONMENT in ["staging", "production"]:
            self._store_id = os.getenv("SHOPIFY_STORE_ID")
            self._token = os.getenv("SHOPIFY_TOKEN_ADMIN")
            self._location_id = os.getenv("SHOPIFY_LOCATION_ID")
            self._webhook_secret = os.getenv("SHOPIFY_SECRET_WEBHOOK")
        else:
            self._store_id = os.getenv("SHOPIFY_DEV_STORE_ID")
            self._token = os.getenv("SHOPIFY_DEV_TOKEN")
            self._location_id = os.getenv("SHOPIFY_DEV_LOCATION_ID")
            self._webhook_secret = os.getenv("SHOPIFY_DEV_SECRET_WEBHOOK")

        timeout_str = os.getenv("SHOPIFY_TIMEOUT_SECONDS")
        if not timeout_str:
            raise RuntimeError("Missing env: SHOPIFY_TIMEOUT_SECONDS")
        self._timeout_seconds = int(timeout_str)
        
        retries_str = os.getenv("SHOPIFY_MAX_RETRIES")
        if not retries_str:
            raise RuntimeError("Missing env: SHOPIFY_MAX_RETRIES")
        self._max_retries = int(retries_str)

    @property
    def timeout_seconds(self) -> int:
        return self._timeout_seconds

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @property
    def token(self) -> str:
        if not self._token:
            raise RuntimeError("Shopify token is not set")
        return self._token

    @property
    def webhook_secret(self) -> str:
        if not self._webhook_secret:
            raise RuntimeError("Shopify webhook secret is not set")
        return self._webhook_secret

    @property
    def location_id(self) -> str:
        if not self._location_id:
            raise RuntimeError("Shopify location id is not set")
        return self._location_id

    @property
    def store_id(self) -> Optional[str]:
        if not self._store_id:
            raise RuntimeError("Shopify store id is not set")
        return self._store_id

    @property
    def admin_url(self) -> str:
        return f"https://admin.shopify.com/store/{self._store_id}"

    @property
    def graphql_url(self) -> str:
        return f"https://{self._store_id}.myshopify.com/admin/api/2025-07/graphql.json"

    @property
    def rest_url(self) -> str:
        return f"https://{self._store_id}.myshopify.com/admin/api/2025-07"

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.token,
        }