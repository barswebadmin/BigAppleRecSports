Status: retired (2026-07-01) — deleted from repo
Old paths (all now gone):
- `lib/clients/shopify-client/shop_client.py` (original monorepo home)
- `backend/lib/clients/shopify-client/shop_client.py` (interim location after user move)
- `backend/src/clients/shopify/shop_client.py` (interim location during Phase 1)

## Why retired

The DSL client's purpose was **dynamic query construction** at runtime — `client.run(schema.customers.queries.by_email, email=..., returns=[...paths])` would build the GraphQL AST by resolving dot-paths against a pickled schema (`DSLSchema(pickled_schema)`).

With ariadne-codegen producing typed pydantic client methods (`client.get_customer(id=...) → GetCustomer`), there's no runtime need for dynamic query building. Every op is a first-class method with baked-in query string and typed pydantic response. The DSL layer became dead weight.

## What went where

- **Query registry / `Resource` primitives / `ResourceId.of`** — obsolete. Codegen client's per-op methods replace `client.run(op, **kwargs)`. `ResourceId.of` (GID normalization from int / numeric / GID / URL) — if needed, port as a small helper into `backend/src/clients/shopify/urls.py` alongside `extract_shopify_id` and `build_shopify_admin_url`. Not urgent.
- **`schema` Box registry** — obsolete. Op names live in the codegen client method names (`client.find_customers(...)`, `client.customer_update(...)`, etc.).
- **`build_selections` + `DSLSchema` machinery** — obsolete. Selection sets are baked into the `.graphql` files, resolved at codegen time.
- **Retry with exponential backoff in `.execute`** — codegen's `client_base.py` doesn't ship retry by default. If BARS wants retry, add it to the hand-written `client_base.py` (`ShopifyBase`) as a decorator or wrap the transport. Small follow-up.

## Runtime deps dropped

- `gql[httpx]==4.0.0` — was only for the DSL client's `DSLSchema` + `HTTPXTransport`. Codegen client uses `httpx` directly.
- `graphql-core==3.2.11` — was pinned only for `pickle.load()` compat with the DSL schema pickle. Ariadne-codegen brings its own `graphql-core<3.3,>=3.2.7` at codegen time via root dev deps.

## The registered ops that were in the DSL registry

Historical record (all now first-class codegen methods):

| DSL registry path | Codegen equivalent |
|---|---|
| `schema.products.queries.by_id` | `client.get_product(id=...)` |
| `schema.products.mutations.update` | `client.product_update(product=...)` |
| `schema.products.mutations.bulk_update_variants` | `client.product_variants_bulk_update(...)` |
| `schema.variants.queries.by_id` | `client.get_variant(id=...)` |
| `schema.customers.queries.by_email` | `client.find_customers(query=f"email:{email}", first=1)` |
| `schema.customers.queries.by_id` | `client.get_customer(id=...)` |
| `schema.customers.mutations.update` | `client.customer_update(input=...)` |
| `schema.orders.queries.by_id` | `client.get_order(id=...)` |
| `schema.orders.queries.by_email` | `client.find_orders(query=f"email:{email}", first=...)` |
| `schema.orders.queries.by_name` | `client.find_orders(query=f"name:{name}", first=1)` |
| `schema.orders.queries.by_product` | `client.find_orders(query=f"product_id:{pid}", first=...)` |
| `schema.orders.mutations.cancel` | `client.order_cancel(...)` |
| `schema.refunds.mutations.create` | `client.refund_create(input=..., idempotency_key=...)` |
