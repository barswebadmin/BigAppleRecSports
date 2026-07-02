Status: keep (new — added 2026-07-01)
Resource: Order
Path: backend/src/clients/shopify/queries/get_order.graphql
Generated: backend/src/clients/shopify/generated/get_order.py (after next `just codegen-shopify` run)

```graphql
query GetOrder($id: ID!) {
  order(id: $id) { ...Order }
}
```

Direct-lookup form; complement to the list/search form (currently `OrdersGet`).

Fragments used: `Order` (which pulls in `Customer`).

**No legacy equivalent** — the old client had `GetOrdersByProduct` / `searchOrders` / `GetAllOrdersForExport` but no direct-by-id order op. Callers used to have to build `orders(query: "id:12345", first: 1)` and unwrap `nodes[0]`. New op:
- Reads primary store (immune to Shopify search-index lag right after mutations).
- Costs 1 point vs ~2 for connection query.
- Returns nullable `Order` directly — no `nodes[0]` unwrap.

Use when caller already has a GID (from a webhook, DB record, or another op).
