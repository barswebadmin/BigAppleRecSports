Status: keep
Resource: Variant
Path: backend/src/clients/shopify/queries/product_variants_bulk_update.graphql
Generated: shopify/generated/product_variants_bulk_update.py

```graphql
mutation ProductVariantsBulkUpdate(
  $productId: ID!, $variants: [ProductVariantsBulkInput!]!
) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    product { id }
    productVariants { id title price }
    userErrors { field message code }
  }
}
```

Absorbs: `BulkUpdateVariantPrices` (same op, smaller selection).
