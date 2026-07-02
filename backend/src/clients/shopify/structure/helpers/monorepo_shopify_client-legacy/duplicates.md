Status: duplicate
Delete: A1 (see `structure/DELETIONS.md#A1`)
Path: `lib/clients/shopify_client-legacy/`
Notes: byte-verified (`shasum`) — every file here except `models/responses.py` is identical to its `backend/lib/clients/shopify_client_old/` counterpart. Full 37-file list in DELETIONS.md.

Only differences from backend:

- **Adds**: `models/responses.py` (tracked separately under `schemas/monorepo_shopify_client-legacy/`; must be preserved before dir deletion).
- **Missing (present in backend)**: `aws_*.sh`, `shopify_client copy.py`, `shopify-requests.curl`, `__pycache__/`.

Blocked on:

1. Deciding fate of `models/responses.py` (`ShopifyResponse` envelope — keep vs drop).
2. Grepping callers of `shopify_client-legacy` / `shopify_client_legacy` imports and marking each `update | delete`.
