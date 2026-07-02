Status: drop
Resource: Customer
Path: backend/lib/clients/shopify_client_old/queries/customers.py → `UpdateCustomerTags`
Replacement: `CustomerUpdate(input: {id, tags})`  — or `TagsUpdate` if the caller doesn't need the customer back

```graphql
mutation updateCustomerTags($input: CustomerInput!) {
  customerUpdate(input: $input) {
    customer { id tags }
    userErrors { field message }
  }
}
```

Same op as new `CustomerUpdate`, smaller selection. Straight substitution.
