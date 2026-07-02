Status: keep
Path: `lib/clients/shopify-client/shop_client.py` → `orders.queries.by_name`
Call site: `client.run(schema.orders.queries.by_name, name=...)`

`orders(query: "name:{name}", first: 1)` DSL wrapper — used to look up an order by its human-readable name (`#1234`). Absorbable into `OrdersGet(query="name:…")`.
