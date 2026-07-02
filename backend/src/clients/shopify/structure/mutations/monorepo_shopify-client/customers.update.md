Status: keep
Path: `lib/clients/shopify-client/shop_client.py` → `customers.mutations.update`
Call site: `client.run(schema.customers.mutations.update, input=CustomerInput(...))`

DSL wrapper for `customerUpdate(input: CustomerInput!)`. Same op as the new `.graphql` `CustomerUpdate` and the legacy `UpdateCustomerTags` — one canonical op survives.
