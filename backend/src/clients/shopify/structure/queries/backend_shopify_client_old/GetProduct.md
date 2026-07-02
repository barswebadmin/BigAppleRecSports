Status: superseded (2026-07-01) — new op `GetProduct` at `backend/src/clients/shopify/queries/get_product.graphql`; tracker at `structure/queries/new/GetProduct.md`. `Product` fragment extracted (`queries/fragments/product.graphql`); `ProductsGet` refactored in the same pass to use `...Product`.
Resource: Product
Path: backend/lib/clients/shopify_client_old/queries/products.py → `GetProduct`
Replacement: **`GetProduct($id: ID!)` + shared `Product` fragment** (superset of legacy selection)

```graphql
query getProduct($id: ID!) {
  product(id: $id) {
    id title handle tags status descriptionHtml createdAt
    variants(first: 5) { nodes { id title inventoryItem { id } inventoryQuantity } }
    media(first: 10)   { nodes { id } }
  }
}
```

Delta vs. new `ProductsGet` selection set:
- Adds `variants.nodes.inventoryItem { id }` — needed by inventory adjust flows.
- Adds `media(first: 10) { nodes { id } }` — needed by media detach flows.
- Loses `importantDates` metafield, `publications`, `totalInventory`,
  `updatedAt`, `sku`/`price`/`inventoryPolicy`/`availableForSale` on variants.

Recommendation: unify by extracting a `Product` fragment with the union of
fields (`inventoryItem{id}`, `media(first:10){nodes{id}}` added to the current
`ProductsGet` selection). Custom `parse_response` flattens `media_ids` — do
that at the call site.
