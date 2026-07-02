Status: drop
Resource: Customer
Path: backend/lib/clients/shopify_client_old/queries/customers.py → `SearchCustomersByEmails`
Replacement: `CustomersGet(query=" OR ".join(f'email:"{e}"' for e in emails), first=len(emails))`

```graphql
query searchCustomers($query: String!, $first: Int!) {
  customers(first: $first, query: $query) { edges { node { id email tags } } }
}
```

Uses `edges { node }` instead of `nodes` — normalize to `nodes` in the new op.
