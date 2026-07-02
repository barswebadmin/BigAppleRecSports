Status: keep (parity with `customers.by_email` pattern)
Path: `lib/clients/shopify-client/shop_client.py` → `orders.queries.by_email`
Call site: `client.run(schema.orders.queries.by_email, email=...)`

`orders(query: "email:{email}", first: …)` DSL wrapper. Absorbable into the new `OrdersGet` with a `"email:…"` query string.
