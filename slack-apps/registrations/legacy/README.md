# `legacy/` — quarantined, going-away code

**Do not refactor anything in this directory.** Move code out only as part of a planned migration.

## Why this exists

Code lives here because it will be deleted once a planned migration completes. Investing refactor
effort here is wasted — the file is going away, not improving.

## Current contents

### `shopify_client/` — Deno-side Shopify direct-post

The Deno workflow handlers used to call Shopify GraphQL directly for two operations:

- Looking up products by handle (admit flow: resolves the waitlist tag)
- Reading/creating/updating customers and their tags (admit flow: applies the waitlist tag)

Both move to the Python `shop_client` (in `lib/clients/shopify-client/`) behind a thin Lambda. The
Deno→Lambda transport replaces every direct Shopify call from this app.

**Latency spike pending** — confirm Deno→Lambda round-trip is acceptable on the interactive admit
path (p50/p95 measurement, decision recorded in-repo) before deleting these files.

**Sole in-app consumer:** `functions/handle_waitlist_actions.ts`. When the consumer switches to the
Lambda transport, this directory disappears.

## When something leaves this directory

It does NOT come back. It either:

- Gets deleted entirely (the migration replaced it).
- Gets rewritten from scratch at the new location (no copying patterns from here).
