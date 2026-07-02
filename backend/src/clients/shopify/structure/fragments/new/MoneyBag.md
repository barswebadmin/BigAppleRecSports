Status: keep (new — added 2026-07-01 for DRY pass)
Path: backend/src/clients/shopify/queries/fragments/money_bag.graphql
Generated: `MoneyBag` in `generated/fragments.py`

```graphql
fragment MoneyBag on MoneyBag {
  shopMoney { ...MoneyV2 }
  presentmentMoney { ...MoneyV2 }
}
```

Composes: `MoneyV2`.

Used by: `Order` fragment (3× at Order level: `totalPriceSet`, `totalDiscountsSet`, `totalRefundedSet`), `Refund` fragment (2×: `totalRefundedSet`, `transactions.nodes.amountSet`).

Rationale: `MoneyBag` shows up 5+ times across order/refund fragments. Every site had `shopMoney { amount }` inlined; a couple wanted `presentmentMoney { amount currencyCode }` instead (`RefundCreate` originally). The unified fragment carries both — accepted overfetch per the "overfetch is OK, DRY first" rule.
