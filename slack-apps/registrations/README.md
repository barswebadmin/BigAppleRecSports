# `registrations` — Slack app

Run-on-Slack (Deno) app that powers BARS registration workflows:

- **Waitlist signups** — webhook → resolve order → write Status column
- **Waitlist admit/remove** — admin modal → Shopify tag + admit email + Status write
- **Refund evaluation** — Lambda posts evaluation card → admin approves/denies → Lambda runs the
  refund
- **Shopify orders export** — modal collects league selections for a downstream Lambda

Deploy and operate per `.claude/skills/slack-app-deploy/SKILL.md`.

### Refund webhook triggers (`Ft…` + `hooks.slack.com/triggers/…`)

**Look up an existing trigger**

```sh
# Defaults to only 4 rows — raise the limit
slack trigger list -w T02HQ2C2G --app deployed  -L 50
slack trigger list -w T02HQ2C2G --app local     -L 50

slack trigger info --trigger-id FtXXXXXXXX -w T02HQ2C2G --app deployed
slack trigger info --trigger-id FtXXXXXXXX -w T02HQ2C2G --app local
```

**Env vars (copy into your real `.env` — see `.env.example`)**

| Variable                         | Where                                                                     | Value                                                                 |
| -------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `SLACK__REFUND_EVAL_TRIGGER_URL` | **Backend** Render (and local `backend` `.env` if you hit submit locally) | **Deployed** trigger URL from `slack trigger create --app deployed …` |
| (same key, different URL)        | While debugging against `slack run`                                       | **Local** trigger URL from `slack trigger create --app local …`       |
| `SLACK__REFUND_TRIGGER_ID_*`     | Optional in **your** `.env`                                               | `Ft…` only for CLI `slack trigger update` / docs — not read by code   |

Hosted Run-on-Slack **secrets** for the app itself: `slack env add …` (see skill). The webhook URL
is for **callers** (FastAPI/Lambda/curl), not for `slack env` unless something in-app reads it.

**Remaining wiring**

1. **Render** — Dashboard → `bars-backend` → Environment → set `SLACK__REFUND_EVAL_TRIGGER_URL` to
   the **deployed** `https://hooks.slack.com/triggers/…` URL → **Manual Deploy** (or push) so the
   new env is picked up.
2. **Optional** — Set `BARS_API_URL` on the **Slack** hosted app
   (`slack env add BARS_API_URL https://…`) so refund approvals hit the BARS API; add that host to
   `manifest.ts` `outgoingDomains` if it is not already there.
3. **Smoke** — With `slack run` active and backend pointing at the **local** trigger URL,
   `POST /refunds/submit` should post the review card to the refund channel.

---

## Directory layout

```
config/        constants & env access; no I/O, no Slack/Shopify SDKs
domain/        league/, waitlist/, refund/ — pure domain logic + I/O modules
  league/        league type, key, format, catalog, selection_state
  waitlist/      types, parse, sheet, planning, execution, dry-run, modal,
                 display, admit email, status write, resolve, debug
  refund/        types, eval_blocks, approve_modal, lambda_requests,
                 orchestrator
shared/        cross-cutting helpers used by domain/ and functions/
  slack/         blocks, modal_state, list_modal, dry_run, diagnostics,
                 workflow (executionId, processorUserId, completers)
  google/        client, gmail, email_message
  http/          prepared_request (request capture for dry-run previews)
  text/          strings, phone, date
functions/     Slack workflow handlers — thin SDK wiring around domain/
workflows/     SDK workflow declarations
triggers/      SDK trigger declarations
tests/         hermetic regression tests (no network)
  refund/        eval-block render + Lambda request shape
  waitlist/      dry-run end-to-end + order-resolution
legacy/        quarantined Shopify direct-post code — do not refactor
manifest.ts    app manifest (functions/workflows/scopes/datastores)
```

### Dependency rules

- `config/` imports nothing from this app.
- `shared/` may import `config/`. May not import `domain/` or `functions/`.
- `domain/` may import `config/` and `shared/`. May not import `functions/`.
- `functions/` may import all of the above. Handlers should be thin (~30–100 lines) — orchestration
  & SDK glue only.
- `legacy/` is opaque. Nothing new imports from it; it imports nothing back.

### Above-the-fold convention

Inside partially-refactored files, refactored code sits at the top of the file under a banner;
not-yet-refactored holdovers sit below under a second banner. Drop the markers once everything's
hoisted.

```ts
// ─── refactored ──────────────────────────────────────────────────────────
// new and relocated code (top-down by call-graph order)

// ─── pending (to be hoisted or deleted) ─────────────────────────────────
// unrefactored holdovers
```

---

## Local workflow

```sh
deno task verify   # type-check + lint + fmt --check
deno task test     # hermetic test suite
deno fmt           # apply formatting (4-space, 100-col)
slack run          # connect local dev app to a Slack workspace
slack deploy       # ship the production app (see slack-app-deploy skill)
```

`deno task verify` is the gate — a broken import path can never silently block a deploy. It
type-checks every TS file under `config/`, `domain/`, `shared/`, `functions/`, `workflows/`,
`triggers/`, and `legacy/`.

---

## Workflow → function map

| Workflow                      | Functions invoked                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------------------- |
| `process_waitlist_signups`    | `fetch_current_waitlists` → admin modal (`handle_waitlist_actions`) → `update_waitlist_spreadsheet` |
| `receive_waitlist_signup`     | `fetch_current_waitlists` → `resolve_waitlist_order` → `update_waitlist_spreadsheet`                |
| `dry_run_waitlist`            | same handler as above; dry-run branch posts previews instead of writes                              |
| `evaluate_refund_request`     | `post_refund_evaluation` (single function: card → modal → Lambda call)                              |
| `get_shopify_orders_workflow` | `get_league_selections_from_modal` → downstream Lambda                                              |

---

## Environment

Local: copy `.env.sample` → `.env`. Reading is centralized in `config/env.ts` — handlers never call
`Deno.env.get` directly.

Production secrets are managed per Slack's hosted env-var system; the same keys are read through
`config/env.ts`.

**Refund approval modal** (`config/store.ts` via `readEnv`): `REFUND_PRIVILEGED_SLACK_USER_IDS` —
comma-separated Slack user IDs allowed to exceed the soft refund estimate without the submit label
switching to "Send to Exec for Approval". Empty/unset means everyone uses the soft-cap label rule.

---

## Conventions

- **4-space indent, 100-column line width.** Enforced by `deno fmt`.
- **No barrels.** Import from the file that owns the symbol.
- **Comments explain _why_, not _what_.** No narration of refactor history.
- **Mutable dataclasses-equivalent.** Domain types are plain `interface`s; builders return new
  objects rather than mutating in place.

See `RESTRUCTURE-PLAN.md` for the full restructure history and acceptance criteria each phase was
held to.
