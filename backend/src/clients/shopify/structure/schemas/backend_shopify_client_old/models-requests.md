Status: decide (call-site convenience — not a GQL concern)
Path: backend/lib/clients/shopify_client_old/models/requests.py

Business-layer wrappers around identifier + pagination shapes:
- `ShopifyOrderIdentifierRequest`, `ShopifyProductIdentifierRequest`, `ShopifyCustomerIdentifierRequest` — accept either a numeric id or a GID and normalize
- `PaginationRequest`, `DateRangeRequest`, `FetchOrderRequest`
- `validate_email_with_results` — email validation helper

Not GQL types. Two paths:
1. Keep as a thin `shopify/requests.py` module — callers still get validated wrappers.
2. Drop and let the call sites pass raw args to codegen client methods.

Recommendation: keep #1 if callers currently rely on the id-or-gid coercion;
otherwise fold `build_shopify_gid` into a helper and drop the wrappers.
