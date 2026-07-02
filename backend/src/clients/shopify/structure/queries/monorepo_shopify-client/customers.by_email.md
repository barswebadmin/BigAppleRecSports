Status: keep (already in DSL registry)
Path: `lib/clients/shopify-client/shop_client.py` → `customers.queries.by_email`
Call site: `client.run(schema.customers.queries.by_email, email=...)`

`customers(query: "email:{email}", first: 1)` DSL wrapper. Same op as legacy `SearchCustomerByEmail` and the new `.graphql` `CustomersGet` — one canonical `.graphql` op fed a `query: "email:…"` string.
