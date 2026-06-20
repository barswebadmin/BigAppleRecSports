"""
Shared configuration for BARS services.

Loads from os.environ using pydantic-settings.
Env var naming: SLACK__DEV_BOT__TOKEN -> slack.dev_bot.token (`__` for nesting)

Usage:
    config = Config()
    config.slack.exec_bot.token
    config.google.service_account  # JSON parsed to dict
"""

import json
import os
import warnings
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Environment Variable Loader ──────────────────────────────────────────────

def load_env_variables(
    required_vars: list[str],
    optional_vars: list[str] | None = None,
    raise_on_missing: bool = True
) -> dict[str, str]:
    """Load environment variables with validation. For Lambda/scripts without full Config."""
    env = {}
    missing = []

    for var in required_vars:
        value = os.environ.get(var)
        if value is None or value == "":
            missing.append(var)
        else:
            env[var] = value

    if missing and raise_on_missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    if optional_vars:
        for var in optional_vars:
            value = os.environ.get(var)
            if value:
                env[var] = value

    return env


class _WarnOnEmpty(BaseSettings):
    """Base for leaf settings. Warns on unset str fields."""
    model_config = SettingsConfigDict(extra="ignore")

    @model_validator(mode="after")
    def _warn_missing(self) -> "_WarnOnEmpty":
        str_fields = {n: v for n, v in self.__dict__.items() if isinstance(v, str)}
        if str_fields and all(not v for v in str_fields.values()):
            return self
        for name, value in str_fields.items():
            if not value:
                warnings.warn(f"{type(self).__name__}.{name} is not set", stacklevel=3)
        return self


# ── Slack ─────────────────────────────────────────────────────────────────────

class SlackBotSettings(_WarnOnEmpty):
    app_id:         str = ""
    token:          str = ""
    signing_secret: str = ""
    webhook_url:    dict[str, str] = {}




class SlackSettings(_WarnOnEmpty):
    dev_bot:                SlackBotSettings           = Field(default_factory=SlackBotSettings)
    exec_bot:               SlackBotSettings           = Field(default_factory=SlackBotSettings)
    leadership_bot:         SlackBotSettings           = Field(default_factory=SlackBotSettings)
    payment_assistance_bot: SlackBotSettings           = Field(default_factory=SlackBotSettings)
    refunds_bot:            SlackBotSettings           = Field(default_factory=SlackBotSettings)
    registrations_bot:      SlackBotSettings           = Field(default_factory=SlackBotSettings)
    web_bot:                SlackBotSettings           = Field(default_factory=SlackBotSettings)



# ── Shopify ───────────────────────────────────────────────────────────────────

class ShopifyTokenSettings(_WarnOnEmpty):
    admin: str = ""


class ShopifyUrlSettings(_WarnOnEmpty):
    admin:        str = ""
    api_graph_ql: str = ""


class ShopifyWebhookSettings(_WarnOnEmpty):
    secret: str = ""


class ShopifySettings(_WarnOnEmpty):
    api_version: str = ""
    location_id: str = ""
    store_id:    str = ""
    token:       ShopifyTokenSettings   = Field(default_factory=ShopifyTokenSettings)
    url:         ShopifyUrlSettings     = Field(default_factory=ShopifyUrlSettings)
    webhook:     ShopifyWebhookSettings = Field(default_factory=ShopifyWebhookSettings)


# ── Google ────────────────────────────────────────────────────────────────────

class GoogleSheetSettings(_WarnOnEmpty):
    order_details__url: str = ""


class GoogleWebAppSettings(_WarnOnEmpty):
    id: str = ""              # GOOGLE__WEB_APP__ID
    url: str = ""             # GOOGLE__WEB_APP__URL
    refunds__url: str = ""    # GOOGLE__WEB_APP__REFUNDS__URL
    waitlist__url: str = ""   # GOOGLE__WEB_APP__WAITLIST__URL


class GoogleLogoSettings(_WarnOnEmpty):
    bars_crest_light: str = ""


class GoogleSettings(_WarnOnEmpty):
    service_account: dict[str, Any] = {}
    sheet:           GoogleSheetSettings  = Field(default_factory=GoogleSheetSettings)
    web_app:         GoogleWebAppSettings = Field(default_factory=GoogleWebAppSettings)
    logo:            GoogleLogoSettings   = Field(default_factory=GoogleLogoSettings)

    @field_validator("service_account", mode="before")
    @classmethod
    def parse_service_account(cls, v: Any) -> dict[str, Any]:
        if isinstance(v, dict):
            return v
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except json.JSONDecodeError as exc:
                raise ValueError(f"GOOGLE__SERVICE_ACCOUNT is not valid JSON: {exc}") from exc
        return {}

    @model_validator(mode="after")
    def _warn_missing(self) -> "GoogleSettings":
        if not self.service_account:
            warnings.warn("GoogleSettings.service_account is not set", stacklevel=3)
        return self


# ── Square ────────────────────────────────────────────────────────────────────

class SquareSettings(_WarnOnEmpty):
    access_token:   str = ""
    application_id: str = ""


# ── Lambda ────────────────────────────────────────────────────────────────────

class LambdaWebhookRouterSettings(_WarnOnEmpty):
    shopify__url: str = ""


class LambdaSettings(_WarnOnEmpty):
    event_bridge_arn: str = ""
    webhook_router: LambdaWebhookRouterSettings = Field(default_factory=LambdaWebhookRouterSettings)


# ── Root config ───────────────────────────────────────────────────────────────

class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = ""
    slack:       SlackSettings   = Field(default_factory=SlackSettings)
    shopify:     ShopifySettings = Field(default_factory=ShopifySettings)
    google:      GoogleSettings  = Field(default_factory=GoogleSettings)
    square:      SquareSettings | None = None
    lambda_:     LambdaSettings  = Field(default_factory=LambdaSettings, alias="lambda")

