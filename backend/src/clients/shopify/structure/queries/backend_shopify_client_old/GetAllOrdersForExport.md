Status: port (needs its own op or fatter fragment)
Resource: Order
Path: backend/lib/clients/shopify_client_old/queries/export_orders.py → `GetAllOrdersForExport`
Replacement plan: extend `Order` fragment to be a superset (user OK w/ overfetch) OR add `OrderForExport` fragment + `OrdersGetForExport` op

```graphql
query getAllOrdersForExport($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query, sortKey: CREATED_AT, reverse: true) {
    nodes {
      id name legacyResourceId createdAt updatedAt
      displayFinancialStatus displayFulfillmentStatus
      totalPriceSet         { shopMoney { amount currencyCode } }
      currentTotalPriceSet  { shopMoney { amount currencyCode } }
      currentTotalDiscountsSet { shopMoney { amount currencyCode } }
      customAttributes { key value }
      customer { id legacyResourceId email firstName lastName }
      lineItems(first: 10) {
        nodes {
          id name title quantity
          originalUnitPriceSet    { shopMoney { amount currencyCode } }
          discountedUnitPriceSet  { shopMoney { amount currencyCode } }
          totalDiscountSet        { shopMoney { amount currencyCode } }
          customAttributes { key value }
          variant { id legacyResourceId title sku }
          product { id legacyResourceId handle title }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
```

Delta vs. current `Order` fragment:
- Adds `legacyResourceId` on Order / Customer / Variant / Product.
- Adds `displayFinancialStatus`, `displayFulfillmentStatus`.
- Adds `currentTotalPriceSet`, `currentTotalDiscountsSet` money sets.
- Adds `sortKey: CREATED_AT reverse: true` variables — belongs on the op, not the fragment.
- Line items need `name`, `quantity`, three money sets, and `product.handle` + `variant.sku`.
- Uses `first: 10` line items (vs `first: 250`) — bump to 250 for parity? Or accept 250 as export-safe.

Recommendation: single `Order` fragment enriched to this superset; drop the deprecated `customer.email` field and switch to the Customer fragment.
