Status: keep — renamed 2026-07-01 from `ProductsGet` (Find*/Get* convention locked); also refactored to use `Product` fragment which now composes `ProductVariant` + `Metaobject`
Resource: Product
Path: backend/src/clients/shopify/queries/find_products.graphql
Generated: backend/src/clients/shopify/generated/find_products.py

```graphql
query FindProducts($query: String!, $first: Int!, $after: String) {
  products(query: $query, first: $first, after: $after) {
    nodes { ...Product }
    pageInfo { ...PageInfo }
  }
}
```

Fragments used: `Product` (which composes `ProductVariant` + `Metaobject`), `PageInfo`.

Search-form op — pair to direct-lookup `GetProduct`.

Callers to migrate later: any references to `ProductsGet` (the old op name).
