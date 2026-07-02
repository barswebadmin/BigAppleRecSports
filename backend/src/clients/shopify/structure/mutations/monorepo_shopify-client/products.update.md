Status: keep (align with new `ProductUpdate` .graphql)
Path: `lib/clients/shopify-client/shop_client.py` → `products.mutations.update`
Call site: `client.run(schema.products.mutations.update, product=ProductUpdateInput(...))`

DSL wrapper for `productUpdate($product: ProductUpdateInput!)` — uses the non-deprecated `product:` argument (matches the new `.graphql` `ProductUpdate`, NOT the legacy `UpdateProduct` which still uses `input: ProductInput!`).
