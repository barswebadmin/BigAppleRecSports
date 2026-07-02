Status: keep
Path: `lib/clients/shopify-client/shop_client.py` → `customers.queries.by_id`
Call site: `client.run(schema.customers.queries.by_id, id=...)`

`customer(id: ID!)` direct fetch. Same shape as legacy `GetCustomer`. Should be a `customer_get.graphql` op reusing the `Customer` fragment.
