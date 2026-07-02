Status: keep (new — added 2026-07-01)
Resource: Customer
Path: backend/src/clients/shopify/queries/get_customer.graphql
Generated: backend/src/clients/shopify/generated/get_customer.py (after next `just codegen-shopify` run)

```graphql
query GetCustomer($id: ID!) {
  customer(id: $id) { ...Customer }
}
```

Direct-lookup form; complement to the list/search form `ProductsGet`-style (currently `CustomersGet`).

Fragments used: `Customer`.

Subsumes legacy `GetCustomer` (from `queries/customers.py`, was single-field selection `{ id email tags }`) — new op uses the full `Customer` fragment (non-deprecated `defaultEmailAddress.emailAddress` + `defaultPhoneNumber.phoneNumber`).

Callers to migrate later: legacy import path `from lib.clients.shopify_client_old.queries.customers import GetCustomer`.
