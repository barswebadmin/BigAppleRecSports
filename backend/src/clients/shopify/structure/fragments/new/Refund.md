Status: keep (new — added 2026-07-01 for DRY pass)
Path: backend/src/clients/shopify/queries/fragments/refund.graphql
Generated: `Refund` in `generated/fragments.py`

```graphql
fragment Refund on Refund {
  id
  note
  createdAt
  totalRefundedSet { ...MoneyBag }
  transactions(first: 10) {
    nodes {
      id
      gateway
      kind
      status
      createdAt
      amountSet { ...MoneyBag }
    }
  }
  order {
    id
    name
  }
}
```

Composes: `MoneyBag` (which in turn composes `MoneyV2`).

Used by: `Order` fragment (`refunds { ...Refund }` — array of refunds on an order), `RefundCreate` mutation (`refund { ...Refund }` — the newly created refund).

Rationale: both sites want the same core refund shape. Previously `Order.refunds` inlined a shopMoney-only selection and `RefundCreate` inlined a presentmentMoney-only selection — divergent for no good reason. Unified fragment (via `MoneyBag`) covers both. Includes `order { id name }` — mild overfetch inside `Order.refunds` (fetches the same order's id/name again per refund) but preserves DRY.
