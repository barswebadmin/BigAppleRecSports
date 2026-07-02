Status: keep (superset of legacy `GetOrdersByProduct`)
Path: `lib/clients/shopify-client/shop_client.py` → `orders.queries.by_product`
Call site: `client.run(schema.orders.queries.by_product, product_id=..., first=…, after=…)`

`orders(query: "product_id:{pid}", first, after)` DSL wrapper. Same shape as the legacy `GetOrdersByProduct` — absorbs it. Absorbable into `OrdersGet(query="product_id:…")`.
