Status: superseded (2026-07-01) — new op `GetVariant` at `backend/src/clients/shopify/queries/get_variant.graphql` + `ProductVariant` fragment; tracker at `structure/queries/new/GetVariant.md`
Resource: Variant
Path: backend/lib/clients/shopify_client_old/queries/variants.py → `GetVariant`
Replacement: **`GetVariant($id: ID!)` + `ProductVariant` fragment** — superset selection covers both `GetVariant` and `GetInventoryInfo` use cases.

```graphql
query getVariant($id: ID!) {
  node(id: $id) { ... on ProductVariant { id title inventoryItem { id } } }
}
```

Selection is the "ProductVariantBrief" candidate fragment (`id`, `title`,
`inventoryItem{id}`), reusable by `GetInventoryInfo` and the product op.
