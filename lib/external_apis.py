"""Stable external API constants shared across the monorepo.

Import the module-level constants directly:
    from lib.external_apis import GOOGLE_API, SHOPIFY_URL_TEMPLATES
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleApi:
    oauth_token_url: str
    sheets_base: str
    gmail_base: str
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class ShopifyUrlTemplates:
    """URL patterns. Both Python and TypeScript derive actual URLs from
    SHOPIFY__STORE_ID + SHOPIFY__API_VERSION rather than storing full URLs in env.
    Uses {placeholder} syntax — call .format(store_id=..., api_version=...) to expand.
    """
    myshopify_domain:   str
    admin_ui:           str
    admin_api_graphql:  str
    storefront_product: str
    customer_admin:     str


GOOGLE_API = GoogleApi(
    oauth_token_url = "https://oauth2.googleapis.com/token",
    sheets_base     = "https://sheets.googleapis.com/v4/spreadsheets",
    gmail_base      = "https://gmail.googleapis.com/gmail/v1",
    scopes          = (
        "https://www.googleapis.com/auth/spreadsheets",
        "https://mail.google.com/",
    ),
)

SHOPIFY_URL_TEMPLATES = ShopifyUrlTemplates(
    myshopify_domain   = "{store_id}.myshopify.com",
    admin_ui           = "https://admin.shopify.com/store/{store_id}",
    admin_api_graphql  = "https://{store_id}/admin/api/{api_version}/graphql.json",
    storefront_product = "https://www.{org_domain}/products/{handle}",
    customer_admin     = "https://admin.shopify.com/store/{store_id}/customers/{customer_id}",
)
