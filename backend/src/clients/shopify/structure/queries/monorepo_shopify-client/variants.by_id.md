Status: keep
Path: `lib/clients/shopify-client/shop_client.py` → `variants.queries.by_id`
Call site: `client.run(schema.variants.queries.by_id, id=...)`

`node(id: ID!) { … on ProductVariant { … } }` fetch via DSL. Aligns with the legacy `GetVariant` / `GetInventoryInfo` — should be a single `.graphql` op with a `ProductVariantBrief`-style fragment covering both call cases.
