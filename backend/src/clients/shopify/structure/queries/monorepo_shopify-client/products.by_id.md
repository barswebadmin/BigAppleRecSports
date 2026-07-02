Status: keep (already in DSL registry; align with `.graphql` op)
Path: `lib/clients/shopify-client/shop_client.py` → `products.queries.by_id`
Call site: `client.run(schema.products.queries.by_id, id=...)`

Direct `product(id: ID!)` fetch via DSL. Fields declared as dot-paths on the `QueryOp` (see `shop_client.py:338`). Overlaps with the new `.graphql` `ProductsGet` (which does `products(query:, first:, after:)`).

Reconcile: keep the direct-id lookup as `product_get.graphql` (single-resource) alongside `products_get.graphql` (list). DSL registry gets both.
