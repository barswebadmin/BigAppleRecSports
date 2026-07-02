Status: superseded (2026-07-01) — new op `GetCustomer` written to `backend/src/clients/shopify/queries/get_customer.graphql`; tracker at `structure/queries/new/GetCustomer.md`
Resource: Customer
Path: backend/lib/clients/shopify_client_old/queries/customers.py → `GetCustomer`
Replacement: **`GetCustomer($id: ID!)` — direct-lookup form** (matches legacy semantics with the richer `Customer` fragment)

```graphql
query getCustomer($id: ID!) {
  customer(id: $id) { id email tags }
}
```

Fields returned: `id`, `email` (deprecated), `tags`. Migrate callers to
`CustomersGet` and use `defaultEmailAddress.emailAddress` from the fragment.
