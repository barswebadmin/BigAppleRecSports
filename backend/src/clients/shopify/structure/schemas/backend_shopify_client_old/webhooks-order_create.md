Status: migrated (2026-07-01) — Phase 2 relocation
Old path: backend/lib/clients/shopify_client_old/models/webhooks/order_create.py (dir now deleted)
New path: **backend/src/webhooks/shopify/order_create.py**

Webhook payload models — Shopify webhook body shape, not admin GQL responses.
Different lifecycle, different keys (snake_case JSON aliases, `WebhookBase`
config), belongs in a webhook module.

Classes: `Address`, `CustomerAddress`, `Customer`, `ClientDetails`,
`NoteAttribute`, `LineItemProperty`, `AttributedStaff`, `LineItem`,
`ShippingLine`, `OrderCreateWebhook`, `OrderLineItemResult`, `OrderCreateResult`.

Plus: `process_order_create(order: OrderCreateWebhook) -> OrderCreateResult`.

Move alongside `models/base.py` (`WebhookBase`, `MoneySet`, `PriceSet`).
