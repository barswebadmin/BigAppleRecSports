"""Feature flags skeleton — Powertools + AppConfig.

FeatureFlags evaluates named flags from an AppConfig configuration profile.
Flags can carry rules (e.g. "refund_dry_run is ON when is_test=true") that
are evaluated against a context dict at runtime — no redeploy to toggle.

Usage (in a function's main.py)
--------------------------------
    from powertools.feature_flags import make_feature_flags

    # Module-level: connection + local cache reused across warm invocations.
    flags = make_feature_flags("ShopifyRefundHandler")

    def lambda_handler(event, context):
        dry_run: bool = flags.evaluate(
            name="refund_dry_run",
            context={"is_test": body.get("is_test", True)},
            default=False,
        )
        active: list[str] = flags.get_enabled_features(context={"is_test": True})

Required AWS resources
-----------------------
AppConfig application   e.g. "ShopifyRefundHandler"
AppConfig environment   matches BARS_ENV (prod / staging / dev)
AppConfig config profile  "flags" (JSON, Powertools feature flag schema)

Schema reference: https://docs.powertools.aws.dev/lambda/python/latest/utilities/feature_flags/

TODO: create AppConfig resources per function that opts in.
"""

import os

from aws_lambda_powertools.utilities.feature_flags import AppConfigStore, FeatureFlags


def make_feature_flags(
    application: str,
    *,
    environment: str | None = None,
    configuration: str = "flags",
) -> FeatureFlags:
    """Return a FeatureFlags instance backed by AWS AppConfig.

    Call once at module level so the AppConfig SDK reuses its connection and
    local TTL cache across warm invocations.

    Parameters
    ----------
    application     AppConfig application name (typically the Lambda function name).
    environment     AppConfig environment (default: BARS_ENV env var → "prod").
    configuration   AppConfig configuration profile name (default: "flags").
    """
    env = environment or os.environ.get("BARS_ENV", "prod")
    store = AppConfigStore(environment=env, application=application, name=configuration)
    return FeatureFlags(store=store)
