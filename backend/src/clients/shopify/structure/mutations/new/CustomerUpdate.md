Status: keep
Resource: Customer
Path: backend/src/clients/shopify/queries/customer_update.graphql
Generated: shopify/generated/customer_update.py

```graphql
mutation CustomerUpdate($input: CustomerInput!) {
  customerUpdate(input: $input) {
    customer { ...Customer }
    userErrors { field message }
  }
}
```

Fragments used: `Customer`.

Absorbs: `UpdateCustomerTags` — pass `{id, tags}` in the `CustomerInput`.
