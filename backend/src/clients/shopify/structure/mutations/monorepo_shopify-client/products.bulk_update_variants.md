Status: keep
Path: `lib/clients/shopify-client/shop_client.py` → `products.mutations.bulk_update_variants`
Call site: `client.run(schema.products.mutations.bulk_update_variants, productId=..., variants=[...])`

`productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!)`. Same op as the new `.graphql` `ProductVariantsBulkUpdate` and the legacy `BulkUpdateVariantPrices` — one canonical op survives.

Constant `TAGS_ADD_BATCH_SIZE` (imported by `add_tag_to_customers.py`) is defined in the same module and paces bulk mutations against Shopify's per-call limits.
