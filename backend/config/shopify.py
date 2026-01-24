import os
from typing import Optional


def _getenv_with_fallback(underscore_key: str, dot_key: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    """Get env var with fallback: try underscore key, then dot notation key."""
    value = os.getenv(underscore_key)
    if value:
        return value
    if dot_key:
        value = os.getenv(dot_key)
        if value:
            return value
    return default


class ShopifyConfig:
    def __init__(self, ENVIRONMENT: str):
        # Environment-specific Shopify configuration
        if ENVIRONMENT in ["staging", "production"]:
            # Use production Shopify credentials for staging and production
            # Support both underscore and dot notation for backward compatibility
            self._store_id = _getenv_with_fallback("SHOPIFY_STORE_ID", "SHOPIFY.STORE_ID") or os.getenv("SHOPIFY_STORE")
            self._token = _getenv_with_fallback("SHOPIFY_TOKEN_ADMIN", "SHOPIFY.TOKEN.ADMIN") or os.getenv("SHOPIFY_TOKEN")
            self._location_id = _getenv_with_fallback("SHOPIFY_LOCATION_ID", "SHOPIFY.LOCATION_ID") or os.getenv("SHOPIFY_DEFAULT_LOCATION_ID")
        else:
            # Use dev/test Shopify credentials (if any) or defaults
            self._store_id = _getenv_with_fallback("SHOPIFY_DEV_STORE", "SHOPIFY.DEV.STORE", "SHOPIFY_DEV_STORE")
            self._token = _getenv_with_fallback("SHOPIFY_DEV_TOKEN", "SHOPIFY.DEV.TOKEN", "SHOPIFY_DEV_TOKEN")
            self._location_id = _getenv_with_fallback("SHOPIFY_DEV_LOCATION_ID", "SHOPIFY.DEV.LOCATION_ID", "SHOPIFY_DEV_LOCATION_ID")

    @property
    def token(self) -> str:
        if not self._token:
            raise RuntimeError("Shopify token is not set")
        return self._token

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