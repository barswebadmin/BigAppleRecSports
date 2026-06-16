---
name: slack-app-deploy
description: How to develop, validate, and deploy the `registrations` Slack app (Run-on-Slack / Deno). Use whenever editing anything under slack-apps/registrations, creating or updating Slack workflows/triggers/functions, running the app locally, adding Slack secrets, or deploying. Covers the slack CLI commands, app IDs, integrations, and the edit → run-local → deploy loop.
---

# Updating the `registrations` Slack app

`slack-apps/registrations/` is a **Run-on-Slack (ROSI)** Deno app: code is
Slack-hosted and deployed with the **`slack` CLI** (already installed and
authed). This is the new Slack Deno platform — it does **not** use Deno Deploy or
the `ddp_`/`ddo_` Deno tokens in the repo `.env` (those belonged to the retired
`registrations-bot`). Auth is the slack CLI session; verify with `slack auth list`.

## Identity (do not hardcode elsewhere)

- Workspace: **bigapplerec** — team `T02HQ2C2G`
- Deployed (production) app: **`A0APE51NYLE`**
- Local dev app: **`A0APV2XGAKT`** (used by `slack run`)
- Linkage lives in `slack-apps/registrations/.slack/apps.json` (deployed) and
  `apps.dev.json` (local).

## Secrets / config

Functions read secrets from the `env` arg (ROSI) by **name** — never commit values:

- `GOOGLE__SERVICE_ACCOUNT` — service-account JSON (Sheets + Gmail)
- `SHOPIFY__URL__API_GRAPH_QL`, `SHOPIFY__TOKEN__ADMIN` — Shopify Admin GraphQL
- Refund Lambda URL is a constant in `config.ts` (`REFUND_PROCESS_URL`), not a secret.

Where they come from:

- **Local (`slack run`):** read from `slack-apps/registrations/.env`.
- **Deployed:** must be added to the hosted app with `slack env add` (they are
  **not** taken from `.env`). List with `slack env list`.

## The loop: edit → validate locally → deploy

Always validate locally before deploying. Run all commands from
`slack-apps/registrations/`.

1. **Type/lint/format gate:**
   ```bash
   deno task verify   # deno check + deno lint + deno fmt --check
   ```
2. **Run locally** (serves local code, hot-reloads, connects via the local dev app):
   ```bash
   slack run --app local -w T02HQ2C2G --hide-triggers --skip-update
   ```
3. **Create a trigger link** pointing at the local app, then click it in Slack to
   exercise the *local* code:
   ```bash
   slack trigger create --app local -w T02HQ2C2G --trigger-def triggers/<name>.ts
   ```
   (Local triggers only fire while `slack run` is active.)
4. **Deploy** once validated:
   ```bash
   slack deploy -w T02HQ2C2G
   ```
5. **Create/refresh the deployed trigger** (separate from the local one; share its
   URL with users):
   ```bash
   slack trigger create --app deployed -w T02HQ2C2G --trigger-def triggers/<name>.ts
   # update an existing one:
   slack trigger update --trigger-id <Ft...> --trigger-def triggers/<name>.ts
   ```
6. **Logs / debugging:** `slack activity --tail`. Manage deployed secrets with
   `slack env add KEY value -w T02HQ2C2G` / `slack env list`.

Notes:
- New workflows must be registered in `manifest.ts`; any external host a function
  calls must be listed in `manifest.ts` `outgoingDomains` or the fetch is blocked.
- `slack run` without `--hide-triggers` will interactively prompt to create
  triggers — pass the flag for non-interactive starts.

## Architecture (registrations/)

- **`manifest.ts`** — registers workflows, `outgoingDomains`, custom `types`, and
  `botScopes`.
- **`functions/`** — `SlackFunction` handlers (the units of logic; open modals,
  call integrations, post messages, handle block actions / view submissions).
- **`workflows/`** — `DefineWorkflow` step chains that sequence functions.
- **`triggers/`** — entry points: link/shortcut triggers (run in a channel) and
  webhook triggers (e.g. inbound refund evaluation).
- **`lib/`** — `clients/` (google, shopify), `slack/` (block/modal builders like
  `list_modal.ts`), `waitlists/` (sheet parsing + display formatting).
- **`types/`, `utils/`, `config.ts`** — shared types, formatters, and config
  (leagues, sheet IDs/tabs, channel routing, the refund Lambda URL).

Two features today:
- **Waitlist** — `check_waitlist` (read-only view) and `process_waitlist`
  (admit/remove, with Shopify tagging, Gmail admit email, sheet status write-back).
- **Refund review** — `evaluate_refund_request` (renders the review card from the
  Lambda payload) and the approve/deny flow.

## Third-party integrations (and where they're wired)

- **Google Sheets + Gmail** — `lib/clients/google/client.ts`. JWT service-account
  auth (`GOOGLE__SERVICE_ACCOUNT`) with domain-wide delegation as
  `web@bigapplerecsports.com`. Used by the waitlist workflows to read responses,
  write status back, and send admit emails. Domains: `*.googleapis.com`,
  `sheets.googleapis.com`, `gmail.googleapis.com`, `oauth2.googleapis.com`.
- **Shopify Admin GraphQL** — `lib/clients/shopify/client.ts`
  (`createShopifyClient` reads `SHOPIFY__URL__API_GRAPH_QL` + `SHOPIFY__TOKEN__ADMIN`).
  Used on admit to find/create + tag the customer (`{handle}-waitlist`) and to look
  up product handles. Domain: `09fe59-3.myshopify.com`.
- **ShopifyRefundHandler Lambda** — `config.ts` `REFUND_PROCESS_URL`. The refund
  approval POSTs the confirmed refund here; the inbound `evaluate_refund_request`
  webhook trigger receives the Lambda's structured evaluation payload to render.
  Domain: the `*.lambda-url.us-east-1.on.aws` host (must be in `outgoingDomains`).

## Keep this skill current

Update this file on any **material** change: new/removed workflow, trigger, or
function; a new or removed third-party integration (and its `outgoingDomains` /
secret names); manifest scope changes; app ID / workspace changes; secret-name
changes; or a change to the run/deploy commands.
