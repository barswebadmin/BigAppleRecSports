Status: keep
Path: `lib/clients/shopify-client/shop_client.py` → `orders.mutations.cancel`
Call site: `client.run(schema.orders.mutations.cancel, orderId=..., reason=..., restock=..., notifyCustomer=..., staffNote=..., refundMethod=...)`

DSL wrapper for `orderCancel(...)` — matches the new `.graphql` `OrderCancel` variable set exactly, including the async `job { id done }` result and the `orderCancelUserErrors` (not `userErrors`) key.
