Status: migrated (2026-07-01) — Phase 2 relocation
Old path: backend/lib/clients/shopify_client_old/models/webhooks/product_update.py (dir now deleted)
New path: **backend/src/webhooks/shopify/product_update.py**

Webhook payload models. Classes: `ProductVariant`, `ProductOption`,
`WebhookProductImage`, `MediaPreviewImage`, `ProductMedia`, `VariantGid`,
`ProductCategory`, `ProductUpdateWebhook`, `ProductUpdateResult`.

Plus: `process_product_update(product: ProductUpdateWebhook) -> ProductUpdateResult`.

Move with the other webhook modules.
