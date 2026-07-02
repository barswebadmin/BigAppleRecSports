Status: keep
Path: `lib/clients/shopify-client/shop_client.py` → `refunds.mutations.create`
Call site: `client.run(schema.refunds.mutations.create, input=RefundInput(...), idempotencyKey=...)`

DSL wrapper for `refundCreate($input: RefundInput!, $idempotencyKey: String!) @idempotent(key: $idempotencyKey)` — matches the new `.graphql` `RefundCreate`.

Refund is one of the few ops where result fields lean on `presentmentMoney` (customer-facing currency) instead of `shopMoney` (store currency).
