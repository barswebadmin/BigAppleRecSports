Status: keep — renamed 2026-07-01 from `CustomersGet` (Find*/Get* convention locked)
Resource: Customer
Path: backend/src/clients/shopify/queries/find_customers.graphql
Generated: backend/src/clients/shopify/generated/find_customers.py

```graphql
query FindCustomers($query: String!, $first: Int!, $after: String) {
  customers(query: $query, first: $first, after: $after) {
    nodes { ...Customer }
    pageInfo { ...PageInfo }
  }
}
```

Fragments used: `Customer`, `PageInfo`.

Search-form op — pair to direct-lookup `GetCustomer`. Absorbs (once callers migrate): legacy `SearchCustomerByEmail`, `SearchCustomersByEmails` — both become `FindCustomers` with different `query` strings (`"email:<email>"`, `"email:<a> OR email:<b>"`).

Callers to migrate later: any references to `CustomersGet` (the old op name).
