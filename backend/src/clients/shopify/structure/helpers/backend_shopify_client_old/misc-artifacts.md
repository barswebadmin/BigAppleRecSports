Status: mixed
Delete: A2 (shell scripts + curl) · D4 (CSVs, webhook JSON, curl scratchpad) · B4 (sgqlc JSON dumps)
Paths (all under `backend/lib/clients/shopify_client_old/`):

- `README.md`, `__init__.py` — package metadata for the legacy client. Delete when the dir goes away (rides with B-tier).
- `aws_add_inventory_to_variant.sh`, `aws_move-inv.sh` — **A2**. Hash-identical to `lib/clients/shopify-client/aws_*.sh` (survivor). Deletable once callers confirmed.
- `shopify-requests.curl` — **A2**. Hash-identical to `lib/clients/shopify-client/shopify-requests.curl` (survivor).
- `shopify_orders_for_7590021333086.csv`, `shopify_orders_for_provided_email.csv` — **D4**. One-off exports. Move to `scripts/samples/` or delete.
- `shopify_schema.json` (~9 MB), `shopify_schema_filtered.json` (~8 MB) — **B4**. Raw sgqlc introspection dumps. Superseded by `backend/src/clients/shopify/schema.graphql` + `lib/clients/shopify-client/2026-07.graphql.pickle`.
- `webhook_payloads.json` (~250 KB) — **D4**. Captured webhook payload samples that seeded webhook models.

Blocked on: grep for `.sh` / `.curl` references before removing (unlikely but cheap to confirm).
