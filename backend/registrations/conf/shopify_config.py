from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ShopifyConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SHOPIFY__",
        extra="ignore",
    )

    api_token: str
    api_version: str
    location_id: str
    shop_id: str
    store_id: str
    webhook_secret: str
