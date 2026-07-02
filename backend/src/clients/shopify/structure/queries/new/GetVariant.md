Status: keep (new — added 2026-07-01)
Resource: Variant
Path: backend/src/clients/shopify/queries/get_variant.graphql
Generated: backend/src/clients/shopify/generated/get_variant.py

```graphql
query GetVariant($id: ID!) {
  node(id: $id) {
    ... on ProductVariant { ...ProductVariant }
  }
}
```

Fragments used: `ProductVariant`.

Uses `node(id:)` interface pattern (no direct `productVariant(id:)` root query in Shopify).

Supersedes legacy `GetVariant` + `GetInventoryInfo` (both from `queries/variants.py`) — the `ProductVariant` fragment is a superset that covers both use cases in one op.

Callers to migrate later:
- `GetVariant` — legacy import from `queries/variants.py`
- `GetInventoryInfo` — legacy import from `queries/variants.py`; caller wanted `inventoryQuantity` + `inventoryItem.sku`, both included in `...ProductVariant`
