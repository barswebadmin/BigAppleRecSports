Status: keep (regenerated)
Path: backend/src/clients/shopify/generated/{customer_update,customers_get,order_cancel,orders_get,product_update,product_variants_bulk_update,products_get,refund_create,tags_update}.py

One codegen module per operation, each exposing the top-level response model
(named after the op) with nested pydantic models for each selection set node.
Callers do `client.execute_customer_update(...)` → `CustomerUpdate` pydantic
result.

Also generated:
- `base_model.py` — pydantic `BaseModel` parent w/ `model_config` for Shopify
- `client.py` — the async GraphQL client method surface
- `client_base.py` — HTTP transport
- `exceptions.py` — `GraphQLClientError`, subclasses
- `__init__.py` — reexports
