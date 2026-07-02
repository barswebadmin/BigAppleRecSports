Status: drop
Resource: Product
Path: backend/lib/clients/shopify_client_old/queries/products.py → `UpdateProduct`
Replacement: `ProductUpdate(product: ProductUpdateInput)` (new, non-deprecated input type)

```graphql
mutation updateProduct($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id title tags media(first: 10) { nodes { id } } }
    userErrors { field message }
  }
}
```

Uses the **deprecated** `ProductInput` argument shape (`input:` vs `product:`).
Callers passing `{"metafields": …}` (e.g. `populate_league_metaobjects.py:619`)
need to switch to `ProductUpdateInput` field naming.

Returned `media { nodes { id } }` needs to appear in the new op or be moved to
a separate `GetProduct` fetch after update.
