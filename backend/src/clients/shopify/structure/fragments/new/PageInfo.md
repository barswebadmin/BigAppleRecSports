Status: keep (new — added 2026-07-01 for DRY pass)
Path: backend/src/clients/shopify/queries/fragments/page_info.graphql
Generated: `PageInfo` in `generated/fragments.py` (after next `just codegen-shopify`)

```graphql
fragment PageInfo on PageInfo {
  hasNextPage
  endCursor
}
```

Composes: nothing (leaf fragment).

Used by: `CustomersGet`, `OrdersGet`, `ProductsGet` — every paginated op spreads it instead of inlining `hasNextPage` + `endCursor`.
