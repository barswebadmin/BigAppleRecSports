Status: keep (new — added 2026-07-01)
Resource: Product
Path: backend/src/clients/shopify/queries/get_product.graphql
Generated: backend/src/clients/shopify/generated/get_product.py (after next `just codegen-shopify` run)

```graphql
query GetProduct($id: ID!) {
  product(id: $id) { ...Product }
}
```

Direct-lookup form; complement to the list/search form `ProductsGet`.

Fragments used: `Product` (new — see `structure/fragments/new/Product.md`).

Subsumes legacy `GetProduct` (from `queries/products.py`) — new op reuses the shared `Product` fragment, which is a superset of legacy `GetProduct`'s selection (adds `inventoryItem { id }` on variants, `media(first: 10) { nodes { id } }`, and the metafield/publications selections that legacy lacked).

`ProductsGet` was refactored in the same pass to use `...Product` — no more inline duplication.

Callers to migrate later: legacy import path `from lib.clients.shopify_client_old.queries.products import GetProduct`. Custom `parse_response` flattened `media_ids` — replicate at call site if needed.
