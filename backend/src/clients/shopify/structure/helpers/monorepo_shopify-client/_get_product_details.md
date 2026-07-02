Status: out-of-scope (one-off script — relocate)
Path: `lib/clients/shopify-client/_get_product_details.py` (56 lines)

Single function `fetch(pid: str) -> dict` that pulls a product's details via `shop_client.ShopifyClient` — smoke-test / manual CLI, not part of the library API. Leading-underscore filename signals it.

Move to a `scripts/` dir alongside `add_tag_to_customers.py`, or delete if it's just dev scaffolding.
