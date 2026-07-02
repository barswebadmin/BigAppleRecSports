Status: keep (new — added 2026-07-01 for DRY pass)
Path: backend/src/clients/shopify/queries/fragments/money_v2.graphql
Generated: `MoneyV2` in `generated/fragments.py`

```graphql
fragment MoneyV2 on MoneyV2 {
  amount
  currencyCode
}
```

Composes: nothing (leaf fragment).

Used by: `MoneyBag` fragment (spread twice — once for `shopMoney`, once for `presentmentMoney`).

Rationale: `MoneyV2` is Shopify's generic "amount + currency" value type. Extracting the fragment means the two `MoneyV2!` fields inside `MoneyBag` share one codegen class.
