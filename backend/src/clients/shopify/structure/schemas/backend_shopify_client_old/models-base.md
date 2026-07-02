Status: migrated (2026-07-01) — Phase 2 relocation with the webhook modules
Old path: backend/lib/clients/shopify_client_old/models/base.py (dir now deleted)
New path: **backend/src/webhooks/shopify/base.py**

Classes:
- `WebhookBase(BaseModel)` — pydantic config for webhook payloads (alias generators, populate_by_name, etc.)
- `MoneySet(WebhookBase)`
- `PriceSet(WebhookBase)`

Used by `webhooks/order_create.py` and `webhooks/product_update.py`. Moves
with the webhook modules once we decide their new home.
