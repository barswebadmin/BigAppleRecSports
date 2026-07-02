Status: drop
Resource: Variant
Path: backend/lib/clients/shopify_client_old/queries/products.py → `BulkUpdateVariantPrices`
Replacement: `ProductVariantsBulkUpdate` (new, superset selection)

```graphql
mutation bulkUpdatePrices($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id price }
    userErrors { field message }
  }
}
```

Same op with narrower selection. Straight substitution.
