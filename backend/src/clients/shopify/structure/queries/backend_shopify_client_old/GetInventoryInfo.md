Status: superseded (2026-07-01) — folded into new `GetVariant` op (uses `ProductVariant` fragment which includes `inventoryQuantity` + `inventoryItem{id sku}`); tracker at `structure/queries/new/GetVariant.md`
Resource: Variant
Path: backend/lib/clients/shopify_client_old/queries/variants.py → `GetInventoryInfo`
Replacement: **`GetVariant($id: ID!)` + `ProductVariant` fragment** — same op as its former sibling, superset selection.

```graphql
query getInventoryInfo($variantId: ID!) {
  node(id: $variantId) {
    ... on ProductVariant { id inventoryQuantity inventoryItem { id sku } }
  }
}
```

Delta vs. `GetVariant`: adds `inventoryQuantity` and `inventoryItem.sku`.
User's stance on overfetch says: fold both into one fragment.
