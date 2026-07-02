Status: decide
Target: `backend/src/clients/shopify/responses.py` OR drop (return raw codegen types)
Path: `lib/clients/shopify_client-legacy/models/responses.py`
Notes: only file in `shopify_client-legacy` that is NOT hash-identical to `backend_shopify_client_old`.

Contents (~88 lines):

- `class ShopifyResponseKind(str, Enum)` — `OK`, `NO_CONTENT`, `NOT_FOUND`, `UNAUTHORIZED`, `FORBIDDEN`, `BAD_REQUEST`, `NOT_ACCEPTABLE`, `UNPROCESSABLE_ENTITY`, `MULTI_STATUS`, `SERVER_ERROR`, `UNEXPECTED_ERROR`.
- `class ShopifyResponse(BaseModel)` — wraps every call: `success: bool`, `kind: ShopifyResponseKind`, `data: dict | None`, `message: str | None`, `attempts: dict | None`.
- Classmethod constructors: `Success`, `NoContent`, and (per file continuation) `NotFound`, `Unauthorized`, etc. — mirror the HTTP-status vocabulary.
- `.to_dict()` — drops `None` fields for JSON serialization.

Decision to make: keep this envelope on top of codegen results (adds retry-metadata + status-classification niceness) or return raw codegen pydantic models and let call sites raise instead. Envelope pairs with the `attempts` field emitted by `ShopifyClient.execute`'s retry loop in `shop_client.py`.
