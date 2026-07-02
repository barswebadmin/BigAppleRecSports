Status: keep
Resource: Product
Path: backend/src/clients/shopify/queries/product_update.graphql
Generated: shopify/generated/product_update.py

```graphql
mutation ProductUpdate($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product { id title handle status descriptionHtml }
    userErrors { field message }
  }
}
```

Uses the newer `ProductUpdateInput` (not the legacy `ProductInput` used by the
old `UpdateProduct`). Consider extracting `Product` fragment for the returned
selection when we bring the metafield-update use case in.
