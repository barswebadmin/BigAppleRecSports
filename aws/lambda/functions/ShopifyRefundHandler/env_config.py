"""Environment variable configuration for ShopifyRefundHandler.

The ``scripts/secrets/sync_env_vars_to_lambda.py`` script reads
``REQUIRED_ENV_VARS`` to determine which keys to pull from the root ``.env``
and push to AWS Lambda. Add a key here AND set it in ``.env`` to surface it
on the function.
"""

REQUIRED_ENV_VARS = [
    # Shopify Admin GraphQL — used by shopify_client.ShopifyClient at cold start.
    "SHOPIFY__API_VERSION",
    "SHOPIFY__LOCATION_ID",
    "SHOPIFY__STORE_ID",
    "SHOPIFY__TOKEN__ADMIN",
    # Slack workflow trigger for the refund-evaluation workflow.
    # The URL (https://hooks.slack.com/triggers/<TEAM>/<ID>/<TOKEN>) is itself
    # the credential — no bearer token / signing secret needed for trigger URLs.
    "SLACK__REFUND_EVAL_TRIGGER_URL",
]
