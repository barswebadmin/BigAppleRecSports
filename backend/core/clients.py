"""External-service client singletons and app-wide lifespan.

Wires app config (from ``core.config``) into the framework-agnostic client
classes in ``lib/clients/*``. Each client is instantiated once at module
import; routes / services import the bound module-level name directly.

    from core.clients import shopify
    result = await shopify.orders_get(query="id:12345", first=1)

Lifecycle: ``lifespan`` is the FastAPI startup/shutdown hook. It closes
each client's connection pool gracefully on shutdown.
"""

from contextlib import asynccontextmanager

from core.config import shopify_config
from lib.clients.shopify import ShopifyClient

# ── Singletons ────────────────────────────────────────────────────────────────

shopify = ShopifyClient(
    store_id=shopify_config.store_id,
    api_version=shopify_config.api_version,
    token=shopify_config.admin_token,
)

# google = GoogleClient(...)
# slack = SlackClient(...)


# ── App lifespan ──────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app):
    """FastAPI startup/shutdown. Closes all client connection pools on exit."""
    try:
        yield
    finally:
        await shopify.http_client.aclose()
        # await google.aclose()
        # await slack.aclose()
