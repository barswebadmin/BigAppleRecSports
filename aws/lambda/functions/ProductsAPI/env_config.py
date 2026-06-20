"""
Environment variable configuration for ShopifyProductUpdates Lambda.

The sync_env_vars_to_lambda.py script reads REQUIRED_ENV_VARS to determine
which variables to sync from .env to AWS Lambda.
"""

REQUIRED_ENV_VARS = [
    # ── phase-transition route ────────────────────────────────────────────────
    # DynamoDB table for RegularSeason records.
    "REGULAR_SEASON_TABLE",
    # SSM path for sport→image-GID mapping (used during registration periods).
    "SSM_IMAGES_PATH",
    # SSM path for sport→sold-out-image-GID mapping (used by sold-out-image-check).
    "SSM_SOLD_OUT_IMAGES_PATH",
    # ── all Shopify routes ────────────────────────────────────────────────────
    "SHOPIFY__API_VERSION",
    "SHOPIFY__LOCATION_ID",
    "SHOPIFY__STORE_ID",
    "SHOPIFY__TOKEN__ADMIN",
    "SHOPIFY__URL__ADMIN",
    "SHOPIFY__URL__API_GRAPH_QL",
]
