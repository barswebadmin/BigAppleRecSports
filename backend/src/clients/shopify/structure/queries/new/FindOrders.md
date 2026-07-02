Status: keep — renamed 2026-07-01 from `OrdersGet` (Find*/Get* convention locked)
Resource: Order
Path: backend/src/clients/shopify/queries/find_orders.graphql
Generated: backend/src/clients/shopify/generated/find_orders.py

```graphql
query FindOrders($query: String!, $first: Int!, $after: String) {
  orders(query: $query, first: $first, after: $after) {
    nodes { ...Order }
    pageInfo { ...PageInfo }
  }
}
```

Fragments used: `Order` (which composes `Customer`, `MoneyBag`, `Refund`), `PageInfo`.

Search-form op — pair to direct-lookup `GetOrder`. Absorbs (once callers migrate): legacy `GetOrdersByProduct` (via `query: "product_id:<n> AND created_at:>=…"`), the ad-hoc `searchOrders` from the retired `get_orders_by_contact.py` CLI.

**Does NOT absorb** `GetAllOrdersForExport` — that specialty CSV-report op needs script-only fields (`legacyResourceId`, `displayFinancialStatus`, `displayFulfillmentStatus`, `sortKey: CREATED_AT reverse: true`, fatter line items with `handle`+`sku`). Belongs in a Phase-2 `backend/scripts/shopify/reports/orders_export/` module with its own `.graphql`, not this client op.

Callers to migrate later: any references to `OrdersGet` (the old op name).
