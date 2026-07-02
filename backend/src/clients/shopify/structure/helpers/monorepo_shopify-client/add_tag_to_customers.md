Status: migrated (2026-07-01) — moved to `backend/scripts/shopify/`
Old paths (all gone): `lib/clients/shopify-client/add_tag_to_customers.py`, `backend/lib/clients/shopify-client/add_tag_to_customers.py`, `backend/src/clients/shopify/add_tag_to_customers.py`
New path: **`backend/scripts/shopify/add_tag_to_customers.py`**

## Contents preserved

- Shopify customer-tag bulk update flow.
- Gmail API integration: `base64`, `MIMEMultipart`/`MIMEText`, `google.oauth2.service_account`, `googleapiclient.discovery.build`. `_build_gmail_service(impersonate_user)` uses `GOOGLE__SERVICE_ACCOUNT` env var with domain-wide delegation.
- Date-utility helper `_ordinal_suffix(day)` (formats day-of-month suffixes for email templates).
- Constant `_EMAIL_SEARCH_CHUNK = 25` — OR-chunk size for `customers` search (query length / Shopify limits).

## Broken imports (needs rewrite before it runs)

Currently imports `from shop_client import TAGS_ADD_BATCH_SIZE, ShopifyClient, schema` — `shop_client.py` was retired 2026-07-01.

Migration path:
- `ShopifyClient` — replace with `from clients.shopify import ShopifyClient` (codegen version, typed).
- `schema` (the DSL Box registry) — no equivalent needed. Call codegen methods directly (`client.find_customers(query=..., first=...)`, `client.tags_update(gid=..., tags_to_add=..., tags_to_remove=...)`, etc.).
- `TAGS_ADD_BATCH_SIZE` — was defined in `shop_client.py` as a batching constant. Redefine inline in the script (`TAGS_ADD_BATCH_SIZE = <value>` — check git history for the exact number if not remembered).

Also uses the deleted `shop_client.ShopifyClient.run(schema.customers.mutations.update, ...)` pattern — rewrite to `await client.tags_update(gid=..., tags_to_add=..., tags_to_remove=...)` batched over the OR-chunk.

Not blocking Phase 1/2 completion. User-driven when the script needs to run again.
