Status: drop
Resource: Customer
Path: backend/lib/clients/shopify_client_old/queries/customers.py → `SearchCustomerByEmail`
Replacement: `CustomersGet(query=f"email:{email}", first=1)`

```graphql
query searchCustomer($query: String!) {
  customers(first: 1, query: $query) { nodes { id email tags } }
}
```

Has a custom `parse_response` that returns "Customer not found" when
`nodes` empty — replicate at the call site via checking `nodes` length.
