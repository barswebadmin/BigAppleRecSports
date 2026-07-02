Status: drop
Resource: Order
Path: backend/lib/clients/shopify_client_old/queries/orders.py → `GetOrdersByProduct`
Replacement: `OrdersGet(query=f"product_id:{pid} AND created_at:>={min} AND created_at:<={max}", first=…)`

```graphql
query getOrdersByProduct($query: String!, $first: Int!, $after: String) {
  orders(first: $first, after: $after, query: $query) {
    nodes {
      id name createdAt cancelledAt totalPriceSet { shopMoney { amount currencyCode } }
      customer { id email firstName lastName tags }
      customAttributes { key value }
      lineItems(first: 250) {
        nodes {
          id title quantity
          customAttributes { key value }
          variant { id title }
          product { id }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

Superset vs. the new `Order` fragment:
- `customAttributes` on the Order itself (not just line items) — new fragment lacks it. **Add to Order fragment.**
- `lineItems.nodes.quantity` — new fragment lacks it. **Add to Order fragment.**
- `totalPriceSet.shopMoney.currencyCode` — new fragment only has `amount`. Add if callers need it (or accept losing currency in the migration).
