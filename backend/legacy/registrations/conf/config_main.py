from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from conf.shopify_config import ShopifyConfig


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_bearer_token: str
    shopify: ShopifyConfig = Field(default_factory=ShopifyConfig)
