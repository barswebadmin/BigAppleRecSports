Status: keep (new — added 2026-07-01)
Path: backend/src/clients/shopify/queries/fragments/product_variant.graphql
Generated: `ProductVariant` in `generated/fragments.py`

```graphql
fragment ProductVariant on ProductVariant {
  id
  title
  sku
  price
  inventoryQuantity
  inventoryPolicy
  availableForSale
  inventoryItem { id sku }
}
```

Composes: nothing (leaf).

Used by: `GetVariant`, `Product` fragment (`variants(first: 5) { nodes { ...ProductVariant } }` — refactored 2026-07-01 to remove the inline selection).

Supersedes legacy `GetVariant` + `GetInventoryInfo` (both from `queries/variants.py`) — one fragment covers both use cases (id/title for variant lookup + inventoryQuantity/inventoryItem.sku for inventory workflows). Overfetch acceptable.

Named `ProductVariant` (verbatim to the Shopify type) rather than `Variant` — matches Shopify's own vocabulary and the pattern of other fragments (`Customer`, `Order`, `Product` all match their type names).
