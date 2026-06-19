"""SSM, AppConfig, and DynamoDB parameter helpers with BARS conventions.

SSM Parameter Store
-------------------
    from powertools.parameters import get_ssm_param, get_ssm_params

    # Module-level (cached 5 min across warm invocations):
    SHOPIFY_TOKEN = get_ssm_param("shopify/token", decrypt=True)

    # Fetch all params under a path prefix:
    shopify_config = get_ssm_params("shopify/")

    # Force refresh inside a handler:
    token = get_ssm_param("shopify/token", decrypt=True, force_fetch=True)

All SSM paths are automatically prefixed with /bars/{BARS_ENV}/.

AppConfig (raw config objects)
--------------------------------
    from powertools.parameters import get_app_config

    # Fetch a raw JSON config profile (not the FeatureFlags DSL):
    policy = get_app_config(application="ShopifyRefundHandler", name="refund-policy")

Use get_app_config when you want a structured config dict from AppConfig (e.g.
refund tier percentages, rate windows) without the FeatureFlags evaluation DSL.
For boolean flag evaluation, see powertools.feature_flags.

DynamoDB config table
----------------------
    from powertools.parameters import make_dynamo_config

    config = make_dynamo_config("bars-config")

    # Fetch a single value:
    tier_json = config.get("refund_tiers")

    # Fetch all values under a partition key:
    all_shopify = config.get_multiple("shopify")

Caching
-------
All three providers maintain an in-memory TTL cache across warm invocations.
Default TTL is 300 s. Pass max_age= to override per-call, or force_fetch=True
to bypass entirely.
"""

import os
from typing import Any

from aws_lambda_powertools.utilities.parameters import AppConfigProvider, DynamoDBProvider, SSMProvider

ENV = os.environ.get("BARS_ENV", "prod")
PREFIX = f"/bars/{ENV}"

ssm = SSMProvider()


# ── SSM Parameter Store ────────────────────────────────────────────────────────

def get_ssm_param(
    key: str,
    *,
    decrypt: bool = False,
    max_age: int = 300,
    force_fetch: bool = False,
) -> Any:
    """Fetch /bars/{env}/{key} from SSM Parameter Store."""
    return ssm.get(f"{PREFIX}/{key}", decrypt=decrypt, max_age=max_age, force_fetch=force_fetch)


def get_ssm_params(
    path: str,
    *,
    decrypt: bool = False,
    max_age: int = 300,
    force_fetch: bool = False,
    recursive: bool = True,
) -> dict[str, Any]:
    """Fetch all SSM params under /bars/{env}/{path} as a flat {suffix: value} dict."""
    return ssm.get_multiple(
        f"{PREFIX}/{path}",
        decrypt=decrypt,
        max_age=max_age,
        force_fetch=force_fetch,
        recursive=recursive,
    )


# ── AppConfig (raw config objects) ────────────────────────────────────────────

def get_app_config(
    *,
    application: str,
    name: str,
    environment: str | None = None,
    max_age: int = 300,
    force_fetch: bool = False,
) -> Any:
    """Fetch a raw config profile from AWS AppConfig.

    Returns the profile value as parsed JSON (dict / list) or raw string.
    Does not apply FeatureFlags rule evaluation — use powertools.feature_flags
    for that.

    Parameters
    ----------
    application     AppConfig application name (e.g. "ShopifyRefundHandler").
    name            Configuration profile name (e.g. "refund-policy").
    environment     AppConfig environment (default: BARS_ENV → "prod").
    """
    env = environment or ENV
    provider = AppConfigProvider(environment=env, application=application)
    return provider.get(name, max_age=max_age, force_fetch=force_fetch)


# ── DynamoDB config table ──────────────────────────────────────────────────────
#
# Useful for config that is updated frequently or programmatically (e.g. a
# table of feature toggles managed outside AppConfig, or config written by
# another Lambda). The table schema Powertools expects:
#
#   id   (String, partition key)  — logical config namespace, e.g. "shopify"
#   sk   (String, sort key)       — config key within that namespace
#   value (String)                — the value (JSON string or plain string)
#
# TODO: create a bars-config DynamoDB table if adopting this pattern.

def make_dynamo_config(table_name: str) -> DynamoDBProvider:
    """Return a DynamoDBProvider for the given config table.

    Call once at module level so the connection is reused across warm invocations:

        config = make_dynamo_config("bars-config")

        # Single value (pk="shopify", sk="token"):
        token = config.get("shopify", sort_key="token")

        # All values under pk="shopify":
        shopify_cfg = config.get_multiple("shopify")
    """
    return DynamoDBProvider(table_name=table_name)
