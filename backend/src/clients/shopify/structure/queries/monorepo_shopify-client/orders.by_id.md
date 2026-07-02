Status: keep
Path: `lib/clients/shopify-client/shop_client.py` → `orders.queries.by_id`
Call site: `client.run(schema.orders.queries.by_id, id=...)`

`order(id: ID!)` direct fetch. Complements the new list-form `OrdersGet` — needs its own `order_get.graphql` op reusing the `Order` fragment.
