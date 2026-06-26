"""Shared base models for Shopify webhook payloads."""

from pydantic import BaseModel, ConfigDict, Field


class WebhookBase(BaseModel):
    model_config = ConfigDict(extra="ignore")


class MoneySet(WebhookBase):
    amount: str = "0.00"
    currency_code: str = "USD"


class PriceSet(WebhookBase):
    shop_money: MoneySet = Field(default_factory=MoneySet)
    presentment_money: MoneySet = Field(default_factory=MoneySet)
