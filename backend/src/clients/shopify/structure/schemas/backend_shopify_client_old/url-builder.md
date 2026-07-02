Status: keep (relocate)
Path: backend/lib/clients/shopify_client_old/shopify_url_builder.py
Target: backend/src/clients/shopify/urls.py (or similar helpers module)

Functions:
- `get_shopify_store_id() -> str`
- `extract_shopify_id(gid_or_id: str) -> str` — pulls the numeric slug out of
  a GID or a URL-like string
- `build_shopify_admin_url(...)` — assembles the Shopify admin console URL for
  a given resource

Not GQL, but tightly coupled to the client (callers building deep links to the
admin UI from GraphQL responses). Move under `shopify/` in a helpers module.
