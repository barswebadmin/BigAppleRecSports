# BARS Slack Apps

Slack/Deno applications for Big Apple Rec Sports operations.

## What ships today

### `registrations/` — production

The only production Slack app. Handles waitlist admit/remove + refund evaluation/approval workflows. Deno + `deno-slack-sdk` running on Slack's Run-on-Slack infrastructure.

Surface:
- Waitlist admin (`fetch_current_waitlists` → `handle_waitlist_actions` → `update_waitlist_spreadsheet`)
- Waitlist webhook (`receive_waitlist_signup` → `resolve_waitlist_order`)
- Refund evaluation (`evaluate_refund_request` posted by the Python lambda → `post_refund_evaluation` → approve/deny modal)

Integrations:
| Concern | Lives at | How `registrations` talks to it |
|---|---|---|
| Google Sheets (waitlists, refund log) | `registrations/lib/clients/google/client.ts` | service-account JSON, domain-wide delegation |
| Gmail (waitlist admit emails) | `registrations/lib/clients/google/gmail.ts` | same service account |
| Shopify (admit-path customer tag, product lookup) | `registrations/lib/clients/shopify/` | direct Deno→Shopify GraphQL today; latency spike pending to decide whether to converge on the `shop_client.py` lambda layer (see [`REGISTRATIONS-REFACTOR-PLAN.md`](../REGISTRATIONS-REFACTOR-PLAN.md) Stage 9.0) |
| Refund pipeline | Python lambda `ShopifyRefundHandler` (in `aws/lambda/functions/`) | lambda POSTs the evaluation payload to a Slack trigger URL |

The Python lambda owns refund fetching/validation/estimation. Slack only renders + collects approval. Wire vocabulary is canonical snake_case across Python and TS (`is_test`, `refund_type`, `submitted_at`, `action`).

### `examples/`, `shared/` — aspirational

Scaffolding for a multi-bot future (a hypothetical `marketing-bot`) that hasn't shipped. `registrations/` imports **nothing** from `shared/`. The setup/quick-start docs describe this aspirational architecture, not how `registrations/` actually works.

Files under `shared/`:
- `auth/google_auth.ts`, `google_client.ts`, `firebase_client.ts`, `deno_firebase_admin.ts`, `firebase_http_client.ts` — Firebase + Google clients exposed as `@bars/firebase` / `@bars/google` / `@bars/shared/…` import aliases
- `config/environment.ts` — `loadEnvironment`, `getAdminUserEmail` (runs at import — side effect)
- `env_loader.ts` — direct `.env` parser (currently unreferenced anywhere)
- `types.ts`

Only `examples/create_new_bot.ts` and `examples/experimental/google_sheets_usage.ts` consume `shared/`. Treat `shared/` as a template, not a runtime dependency.

## Directory map

```
slack-apps/
├── registrations/              ← production bot (workflows, functions, triggers, lib, tests)
│   ├── manifest.ts
│   ├── config.ts               (547 lines; decomposition deferred — see WAITLIST-HANDLER-REFACTOR.md)
│   ├── functions/              (Slack-function definitions + handler bodies)
│   ├── workflows/              (multi-step workflows)
│   ├── triggers/               (link/event/scheduled triggers)
│   ├── lib/
│   │   ├── clients/google/     (Sheets, Gmail)
│   │   ├── clients/shopify/    (customer_ops, product_ops, client)
│   │   ├── slack/              (blocks, list_modal, dry_run, refund_*, diagnostics)
│   │   ├── waitlists/          (sheet_service, league_key, display, admit_email, handlers/)
│   │   └── refunds/            (lambda_requests)
│   ├── utils/                  (date_utils, formatters)
│   ├── types/                  (league, evaluation_payload, waitlist_signup_payload)
│   ├── tests/                  (deno test harness — fetch-stubbed, no net access)
│   └── WAITLIST-HANDLER-REFACTOR.md
├── shared/                     ← aspirational shared auth (NOT used by registrations)
├── examples/                   ← templates demonstrating `shared/` usage
├── docs/                       ← setup + deploy + Slack-SDK reference
│   ├── DEPLOYMENT_GUIDE.md
│   ├── QUICK_START.md          (describes the aspirational multi-bot architecture)
│   ├── SETUP_AUTHENTICATION.md (Google domain-wide-delegation setup, still accurate)
│   └── slack-deno-sdk-links.md
└── deno.json                   ← root config + import aliases
```

## Environment

Configure in the monorepo root `.env` (the `slack-apps/deno.json` tasks `bash -c 'source ../.env && …'`). Required by the production `registrations/` bot:

- `GOOGLE__SERVICE_ACCOUNT` — service account JSON (domain-wide delegation enabled)
- `ADMIN_USER_EMAIL` — admin user the service account impersonates for Google API calls
- `DEFAULT_USER_DOMAIN` — typically `bigapplerecsports.com`
- `SHOPIFY__STORE_ID`, `SHOPIFY__API_VERSION`, `SHOPIFY__TOKEN__ADMIN` — used by the Deno-side Shopify client and shared with the Python `shop_client.py` layer
- `SLACK__DENO__PERSONAL_TOKEN` — for `slack deploy`

Domain-wide-delegation OAuth scopes + Google Admin Console setup are documented in [`docs/SETUP_AUTHENTICATION.md`](docs/SETUP_AUTHENTICATION.md).

## Common tasks

From `slack-apps/`:

```bash
# typecheck + lint + run unit tests (no network, no env)
deno task test

# format check
deno task format

# auth smoke tests (require .env in monorepo root)
deno task test-auth          # minimal
deno task test-auth-full     # full shared-auth path
deno task test-all
```

From `slack-apps/registrations/`:

```bash
slack run                    # local development
slack deploy                 # ship to Slack
```

## Architecture notes

**Production approach (registrations/):** self-contained — its own clients, types, formatters. Zero imports from `slack-apps/shared/`. Fast to reason about; easy to deploy as one bundle.

**Aspirational approach (shared/ + examples/):** designed for "many bots, one credential set". Real if/when a second bot ships. Until then it's dead weight that the [`SETUP_AUTHENTICATION.md`](docs/SETUP_AUTHENTICATION.md) and [`QUICK_START.md`](docs/QUICK_START.md) still describe as live — treat their `@bars/firebase` / `@bars/google` import snippets as forward-looking, not as patterns to copy into `registrations/`.

## Related docs

- [`REGISTRATIONS-REFACTOR-PLAN.md`](../REGISTRATIONS-REFACTOR-PLAN.md) (monorepo root) — cross-repo (GAS + AWS + Slack) refactor stages; authoritative for architecture decisions that span the three runtimes.
- [`registrations/WAITLIST-HANDLER-REFACTOR.md`](registrations/WAITLIST-HANDLER-REFACTOR.md) — intra-bot handler decomposition plan.
- [`docs/SETUP_AUTHENTICATION.md`](docs/SETUP_AUTHENTICATION.md) — Google service-account + domain-wide-delegation setup.
- [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) — Deno Deploy paths (note: `registrations/` runs on Slack's Run-on-Slack, not Deno Deploy; this guide is for `shared/`-style standalone Deno apps).
- [`docs/QUICK_START.md`](docs/QUICK_START.md) — multi-bot tutorial against the aspirational `shared/` architecture.
- [`docs/slack-deno-sdk-links.md`](docs/slack-deno-sdk-links.md) — curated Slack/Deno SDK doc index.
