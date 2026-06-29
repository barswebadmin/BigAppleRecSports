# Design: refund-cancel-workflow

> Plan-mode design. Stages 1, 2, and 3 are fully detailed for sub-agent
> execution and can run in parallel. Stages 4–7 remain skeletons + inventories —
> they scope work and call out dependencies, not line-level implementation.

---

## Overview

Today the refund/cancel approval flow is split across three places:

1. A Slack app (`slack-apps/registrations/`) that already renders a refund
   "review card" + approval modal when a Lambda webhook posts an evaluation
   payload (existing refund-evaluation flow, modal lives in
   `views/refund/approve_modal.ts`).
2. A `ShopifyRefundHandler` AWS Lambda that the Slack approval modal POSTs to
   for the actual cancel/refund execution (`REFUND_PROCESS_URL`).
3. A FastAPI backend (`backend/`) with stub `/refunds/*` and `/orders` routes,
   plus several legacy / module-local refund-estimate implementations under
   `backend/legacy/registrations/`, `backend/modules/refunds/`, and
   `backend/modules/orders/`.

**Goal:** drive the existing refund/cancel review flow from a Google Sheet
(operator-curated list of refund requests) instead of from the Lambda webhook,
while consolidating the refund estimate + Shopify mutation logic into the
FastAPI backend so all paths (webhook, sheet-driven, future) call one
service. Slack stays "dumb" — it renders the blocks the backend hands it and
echoes back the operator's selections.

End-to-end:

> Sheet row (unprocessed) → Slack handler (`/eval-refund-request` slash command)
> → `POST /refunds/validate` → reuse existing approval modal →
> `POST /refunds/create` (or `DELETE /orders/{id}`) → Slack confirmation message.

---

## Architecture

High-level sequence (sheet-driven trigger → backend validate → modal → execute → final message):

```mermaid
sequenceDiagram
    autonumber
    participant Op as Operator
    participant Sheet as Google Sheet<br/>(Refund_Requests)
    participant Slack as Slack App<br/>(registrations)
    participant API as FastAPI Backend
    participant Shop as Shopify Admin GQL

    Op->>Slack: /eval-refund-request (or button click)
    Slack->>Sheet: read rows (filter unprocessed by Status column)
    Slack-->>Op: pick a row (modal)
    Slack->>API: POST /refunds/validate ValidateRefundRequest {orderNumber, requestedRefundTo, requesterEmail, ...}
    API->>Shop: order lookup + transactions (consolidated client)
    API-->>Slack: RefundRequestEval {ok, isValid, order, product, estimate, validationErrors?}  (plain dict / TypedDict; NOT Pydantic, NOT Block Kit)
    Slack-->>Op: render review card → operator clicks Approve
    Op->>Slack: submit modal (cancel?, refund?, amount, restockTo?, notify)
    Slack->>API: POST /refunds/create CreateRefundRequest {orderId, productId, refundTo, amount, cancel?, refund?, restockTo?, notify?, approvedBy, isTest?}
    API->>Shop: orderCancel + refundCreate (consolidated client)
    API-->>Slack: {ok, cancel, refund, errors[]}  (controller-built dict; NOT Pydantic, NOT Block Kit)
    Slack-->>Op: post final confirmation message (Slack builds Block Kit locally)
```

### Component inventory

| Layer   | Component                             | Path                                                                                                                     | Status                                                                                                       |
| ------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| Slack   | New entry handler (slash cmd)         | `slack-apps/registrations/functions/send_request_for_eval.ts` (new)                                                      | **Stage 1**                                                                                                  |
| Slack   | Approve-modal builder (generic)       | `slack-apps/registrations/views/_shared/approve_modal.ts` (new — refund-agnostic block builders)                         | **Stage 1**                                                                                                  |
| Slack   | Refund-flavored approve-modal caller  | `slack-apps/registrations/views/refund/approve_modal.ts`                                                                 | UPDATE (thin caller of `_shared/approve_modal.ts`; constant rename)                                          |
| Slack   | Picker-modal builder (generic)        | `slack-apps/registrations/views/_shared/picker_modal.ts` (new — refund-agnostic block builders)                          | **Stage 1**                                                                                                  |
| Slack   | Existing refund eval blocks           | `slack-apps/registrations/views/refund/eval_blocks.ts`                                                                   | refactor in Stage 4                                                                                          |
| Slack   | Refund types (types-only)             | `slack-apps/registrations/domain/refund/types.ts` (new)                                                                  | **Stage 1**                                                                                                  |
| Slack   | Sheet loader (refund-specific)        | `slack-apps/registrations/domain/refund/sheet_loader.ts` (new)                                                           | **Stage 1**                                                                                                  |
| Slack   | Refund typed call-site convenience    | `slack-apps/registrations/domain/refund/api.ts` (new — `validateRefund(client, body)`, `executeRefund(client, body)`)    | **Stage 1**                                                                                                  |
| Slack   | Generic BARS API HTTP client          | `slack-apps/registrations/clients/bars_api/client.ts` (new — refund-agnostic `post<T>`/`get<T>` wrapper)                 | **Stage 1**                                                                                                  |
| Slack   | Generic Google sheet column helper    | `slack-apps/registrations/shared/google/columns.ts` (new — `findColumn(headers, substring)`)                             | **Stage 1**                                                                                                  |
| Slack   | Channel routing                       | `slack-apps/registrations/config/workflows.ts` (existing — uses `SLACK_CHANNEL__REFUNDS__DEFAULT`)                       | update                                                                                                       |
| Backend | `POST /refunds/validate`              | `backend/routes.py` (stub exists, line 84)                                                                               | Stage 2                                                                                                      |
| Backend | `POST /refunds/create`                | `backend/routes.py` (stub exists, line 80)                                                                               | Stage 5                                                                                                      |
| Backend | `DELETE /orders/{id}`                 | `backend/routes.py` (stub exists, line 76)                                                                               | Stage 5                                                                                                      |
| Backend | Estimate service                      | `backend/modules/refunds/services/estimate_service.py` (new)                                                             | **Stage 2**                                                                                                  |
| Backend | Shopify cancel/refund service wrapper | `backend/modules/refunds/services/shopify_refund_service.py` (new — wraps the canonical `schema`-registry client)        | **Stage 3**                                                                                                  |
| Backend | Refunds controller (FastAPI handlers) | `backend/modules/refunds/controllers/refunds_controller.py` (new — thin)                                                 | **Stage 2** + 5                                                                                              |
| Backend | Refund tier-math (pure)               | `backend/modules/refunds/refund_calculator.py` (existing — keep)                                                         | reuse (Stage 2)                                                                                              |
| Backend | Date / money / order utilities        | `backend/utils/dates.py`, `backend/utils/money.py`, `backend/utils/orders.py` (Stage 2 Commits 2.1 / 2.2 / 2.3)          | **Stage 2**                                                                                                  |
| Backend | Date helpers (existing — reuse)       | `backend/utils/date_utils/`, `backend/utils/datetime/`                                                                   | reuse (Stage 2)                                                                                              |
| Lib     | Shopify GQL client (canonical)        | `backend/lib/clients/shopify-client/shop_client.py` (typed schema registry; uses `gql`/`gql.dsl`)                        | reuse as-is (D10; **Stage 3** — no rename)                                                                   |
| Lib     | Mutation registry                     | `schema.orders.mutations.cancel` + `schema.refunds.mutations.create` already present; no extension needed for happy path | **Stage 3** — wrapped by `ShopifyRefundService`                                                              |
| Lib     | Old Shopify client (deprecated)       | `backend/lib/clients/shopify_client/` (underscore, NOT `gql.dsl`-based)                                                  | **Stage 3** — left untouched; documented as deprecated in D10; no migration of pre-existing callers in scope |

## Components and Interfaces

The component inventory table above is the master list. **The principle is
"reusable functions, parameterized by inputs"** — one HTTP wrapper, one
service object, one sheet-row parser, not one function per route or column.
Detailed signatures live inside their respective stage sections below; this
section maps each layer to its 1–3 entry points.

| Layer           | Entry point(s)                                                    | Where   |
| --------------- | ----------------------------------------------------------------- | ------- |
| Slack app       | `send_request_for_eval` (slash-command function) ·                | Stage 1 |
|                 | generic `pickerModal({ items, formatItem, ... })` view ·          | Stage 1 |
|                 | `barsApi.post<T>({ endpoint, body, ... })` (one HTTP wrapper,     | Stage 1 |
|                 | refund-agnostic; refund call sites use thin convenience wrappers  |         |
|                 | in `domain/refund/api.ts`)                                        |         |
| Slack app sheet | `fetchRefundRequests(env)` (parameterized parser; column          | Stage 1 |
|                 | substring tokens are constants)                                   |         |
| FastAPI backend | `EstimateService.compute_estimate(request)` ·                     | Stage 2 |
|                 | `ShopifyRefundService.create_refund(...)` ·                       | Stage 3 |
|                 | `ShopifyRefundService.cancel_order(...)` ·                        | Stage 3 |
|                 | (Stage 5 wires `POST /refunds/create` directly through the        | Stage 5 |
|                 | controller, calling `ShopifyRefundService` methods in sequence —  |         |
|                 | NO orchestrator service. See D30.)                                |         |
| Shopify client  | `ShopifyClient.run(op, **kwargs)` (canonical client at            | Stage 3 |
|                 | `backend/lib/clients/shopify-client/shop_client.py`; `op` is a    |         |
|                 | registry handle: `schema.<resource>.<queries\|mutations>.<name>`) |         |

**Boundary rule.** The backend **never** builds Slack Block Kit. The
`POST /refunds/validate` response (`RefundRequestEval`) is a plain Python
dict / `TypedDict` constructed by the controller — **not** a Pydantic model —
keyed by field/sub-field; the Slack app reads `eval.estimate.original.amount`
directly into its own block builders. Pydantic is reserved for **incoming
external request bodies only**; outgoing responses constructed by the backend
use TypedDict / dataclass / dict (D28). There are no `build_*_blocks` /
`build_*_payload` functions on the backend, no `blocks: list[dict]` field in
any backend response, and no `backend/modules/slack/block_builders/` directory.

## Data Models

These are the contracts crossing the Slack ↔ Backend boundary. Detailed Pydantic
schemas for **incoming** request bodies land in Stages 2/5. The backend's
**outgoing** responses are plain Python dicts / TypedDicts constructed by the
controller — **not Pydantic** (D28: Pydantic is reserved for incoming external
objects). No `blocks: list[dict]` field, no Block Kit, no Slack-SDK coupling
on the backend. The Slack app builds Block Kit from these fields locally.

```typescript
// Slack → Backend (Stage 2)  ── ValidateRefundRequest
POST /refunds/validate
{
  orderNumber: string,                                      // REQUIRED
  requestedRefundTo: "original_method" | "store_credit",    // REQUIRED
  requesterEmail: string,                                   // REQUIRED
  requesterFirstName: string,                               // REQUIRED
  requesterLastName: string,                                // REQUIRED
  notes?: string | null,                                    // OPTIONAL
  transferRequest?: string | null,                          // OPTIONAL
  sheetRowRef?: { spreadsheetId: string, tabId: string, rowNumber: number }, // OPTIONAL
  isTest?: boolean,                                         // OPTIONAL — defaults to false
}
// NOTE: NO `source` field (the request always originates from a sheet —
// there is no other source). NO `slackChannel` field (channel routing is
// resolved fully on the Slack side; backend never receives a channel hint).
// NO `policyConfirmation` field (the form gates submission on it but the
// backend does not consume it; the sheet loader still captures the cell
// value for diagnostic logging only — see Stage 1a).

// Backend → Slack (Stage 2 response shape) ── RefundRequestEval
//   Plain Python dict / TypedDict — NOT Pydantic (D28). Backend constructs
//   it manually; FastAPI controller's response_model is `dict` (or omitted).
{
  ok: boolean,
  isValid: boolean,                       // (replaces validation.matched)
  validationErrors?: string[] | null,     // (replaces validation.mismatches[]; flat string[] only)

  order: {
    id: string,                           // Shopify order GID
    number: string,
    customerName: string,
    email: string,                        // the order's customer email
    amountPaid: number,                   // total paid on the order, in dollars
    currency: string,
  },

  product: {                              // split out of `order`/`season` (was nested)
    id: string,                           // Shopify product GID
    url: string,                          // canonical product URL
    year: number,
    season: string,                       // "Winter" | "Spring" | "Summer" | "Fall"
    sport: string,
    day: string,
    division: string,                     // "WTNB+" | "Open" | ...
    week1Start: string | null,            // ISO date — first session
    week2Start: string | null,
    week3Start: string | null,
    week4Start: string | null,
    week5Start: string | null,
  },

  estimate: {
    original:    { amount: number, percentage: number, tierLabel: string, ... },
    storeCredit: { amount: number, percentage: number, tierLabel: string, ... },
  },
}

// Slack → Backend (Stage 5)  ── CreateRefundRequest
POST /refunds/create
{
  orderId: string,                        // REQUIRED — round-tripped from /validate
  productId: string,                      // REQUIRED — round-tripped from /validate
  refundTo: "original_method" | "store_credit",  // REQUIRED
  amount: number | null,                  // REQUIRED on refund; null when cancel-only
  cancel?: boolean,                       // OPTIONAL — defaults to false
  refund?: boolean,                       // OPTIONAL — defaults to false
  restockTo?: "veteran" | "early" | "general" | "waitlist" | "full",  // OPTIONAL — omit when no restock
  notify?: boolean,                       // OPTIONAL — defaults to false
  approvedBy: string,                     // REQUIRED — Slack user id
  isTest?: boolean,                       // OPTIONAL — defaults to false
}
// NOTE: `restockTo` REPLACES `restock`. No `"none"`, `"no_restock"`, or
// `"admin_hold"` values — the field is omitted entirely when no restock is
// intended. New options `"veteran"`, `"early"`, `"general"` added.

// Backend → Slack (Stage 5 response shape; controller-built dict, NOT Pydantic)
{
  ok: boolean,
  cancel:  CancelOutcome | null,    // { jobId, jobDone } when cancel=true
  refund:  RefundOutcome | null,    // { refundId, amount, currency, createdAt } when refund=true
  errors:  ShopifyUserError[],      // empty on full success
}
```

**Round-trip metadata.** `orderId` and `productId` are echoed back from
`/refunds/validate` to Slack and re-sent on `/refunds/create`. Both are tiny
(GIDs are ~40 chars each) so they sit at the top level of the request — no
opaque `orderMetadata` blob needed, no concerns about Slack
`private_metadata`'s 3 KB ceiling.

---

## Stage Map (parallelization callouts)

| Stage                             | Depends on | Can run in parallel with | Risk                                        | Status       |
| --------------------------------- | ---------- | ------------------------ | ------------------------------------------- | ------------ |
| 1a Slack entry point + sheet read | —          | 2, 3                     | Low — boilerplate-heavy, all infra in place | **Detailed** |
| 1b Modal reuse + `validate` call  | 1a         | 2 (mock the response)    | Low                                         | **Detailed** |
| 1c Channel routing + tests        | 1a, 1b     | 2, 3                     | Low                                         | **Detailed** |
| 2 Refund estimate consolidation   | —          | 1, 3                     | Medium — many existing impls to reconcile   | **Detailed** |
| 3 Shopify request consolidation   | —          | 1, 2                     | Medium — must use lib GQL client            | **Detailed** |
| 4 Validation response shape       | 2, 3       | 5 once contract is fixed | Low                                         | Skeleton     |
| 5 Cancel + refund execution       | 3          | 4 (after contract fix)   | Medium — irreversible Shopify calls         | Skeleton     |
| 6 Final response shape            | 5          | 7                        | Low                                         | Skeleton     |
| 7 Slack final message             | 1, 6       | —                        | Low                                         | Skeleton     |

**Parallelization opportunities (immediately exploitable):**

- **Stages 1, 2, and 3 all run in parallel.** Stage 1 mocks the backend's
  `/refunds/validate` response while Stage 2 builds it; the mock is a few
  lines of JSON returned by the typed `validateRefund(client, body)` wrapper
  in `domain/refund/api.ts` (which, behind the scenes, calls the generic
  `clients/bars_api/client.ts` HTTP wrapper). Stage 3 is independent of
  Stage 1 entirely — it lands `ShopifyRefundService` as the Shopify-side
  foundation Stage 5 consumes.
- **Stage 1a and 1b can run in parallel** (they share no files; 1a is the entry
  point + sheet reader, 1b is the validate call + modal pre-fill).
- **Stage 4 (validation response shape) and Stage 6 (final response shape)** can
  be designed in parallel as soon as the wire shapes are agreed on.

**Cross-stage anchors (no contract surprises during parallel work):**

- **Stage 1 → Stage 2 mock contract.** Stage 1 imports the canonical estimator
  that already exists at `backend/modules/refunds/refund_calculator.py` —
  Stage 2 just consolidates around that path with no API change. Stage 1
  calls `POST /refunds/validate` against a mock response that matches
  `RefundRequestEval` field-for-field; Stage 2 wires the real route and
  returns the same shape.
- **Stage 2 → legacy delete ordering (gating).** Stage 2 rewrites
  `backend/legacy/registrations/services/refunds_service.py`'s import from
  `from utils.refund_calculator import …` to
  `from modules.refunds.refund_calculator import …` **before** deleting the
  legacy duplicate at `backend/legacy/registrations/utils/refund_calculator.py`.
  This ordering is enforced as a Stage 2 acceptance criterion (§ 2.g).
- **Stage 3 independence.** Stage 3 has no Stage 1 / Stage 2 dependencies; it
  introduces `ShopifyRefundService` and rewrites direct
  `client.run(schema.…)` callers in `backend/legacy/services/`. No Stage 1
  mock or Stage 2 controller is required for Stage 3 to ship.

---

## Stage 1 — Slack handler for existing entries [DETAILED]

> This stage lands a working "operator-driven, sheet-backed" refund-review
> trigger that opens the existing approval modal. It calls a placeholder
> `POST /refunds/validate` (Stage 2 owns the real backend). No backend
> implementation is required to ship Stage 1 — the placeholder returns a stub
> response shape that's enough to render the modal.

### 1a — Slack entry point + sheet read

**Decision: slash command vs URL trigger — pick slash command.**

Rationale: a Run-on-Slack app doesn't get URL-trigger inputs from the user
(you'd need a form pre-filled by the operator), and the existing app already
declares `commands` in `botScopes` (`slack-apps/registrations/manifest.ts`
line 36). A slash command launches a workflow with `interactivity` already
populated, which is exactly what the existing modal needs (every other modal
flow in the app — `handle_waitlist_actions.ts`, `get_league_selections_from_modal.ts`
— takes `interactivity` as input).

#### Final naming alignment (Stage 1)

| Layer         | Identifier                | File                                   |
| ------------- | ------------------------- | -------------------------------------- |
| Slash command | `/eval-refund-request`    | (registered via Slack CLI)             |
| Trigger       | `start_refund_eval`       | `triggers/start_refund_eval.ts`        |
| Workflow      | `validate_refund_request` | `workflows/validate_refund_request.ts` |
| Function      | `send_request_for_eval`   | `functions/send_request_for_eval.ts`   |

The slash command lives entirely inside the existing `registrations` Slack app
— no new app, no new manifest, just a new workflow + trigger + function +
slash-command shortcut.

**Slash command name: `/eval-refund-request`** (D1).

#### Files to create

```
slack-apps/registrations/
├── clients/bars_api/
│   └── client.ts                                 (new — generic BARS API HTTP wrapper, refund-agnostic)
├── domain/refund/
│   ├── types.ts                                  (new — RefundSheetEntry, RefundSheetData, RefundTo, etc.)
│   ├── sheet_loader.ts                           (new — fetchRefundRequests + parseRow logic; refund-specific column tokens)
│   └── api.ts                                    (new — typed validateRefund/executeRefund convenience wrappers around bars_api/client)
├── functions/
│   └── send_request_for_eval.ts                  (new — orchestrator, mirrors handle_waitlist_actions.ts)
├── triggers/
│   └── start_refund_eval.ts                      (new — shortcut trigger for the slash command)
├── views/
│   ├── _shared/
│   │   ├── picker_modal.ts                       (new — generic, parameterized list-modal block builder)
│   │   └── approve_modal.ts                      (new — generic, parameterized approval-modal block builders)
│   └── refund/
│       └── approve_modal.ts                      (UPDATE — thin caller of views/_shared/approve_modal.ts; constant rename)
│       (the OLD pick_row_modal.ts is DELETED — refund flow now uses views/_shared/picker_modal.ts directly)
├── shared/google/
│   └── columns.ts                                (new — generic findColumn helper)
├── workflows/
│   └── validate_refund_request.ts                (new — wires the trigger → send_request_for_eval)
└── manifest.ts                                   (UPDATE — register validate_refund_request workflow; "commands" scope already present)
```

> Removed from prior draft: `domain/refund/sheet_format.ts` (highlight-based
> processed-row detection is dropped permanently — the `Status` column is the
> only source of truth) and `domain/refund/sheet.ts` (split into `types.ts`
>
> - `sheet_loader.ts` per D26). The old `domain/refund/api_client.ts`
>   listing is replaced by the smaller `domain/refund/api.ts` typed
>   call-site convenience layer (the HTTP wrapper itself moved to
>   `clients/bars_api/client.ts`).

#### Function signatures (Deno/TypeScript)

```typescript
// domain/refund/types.ts  (types only — no functions)
export type RefundTo = "original_method" | "store_credit";

export interface RefundSheetEntry {
  rowNumber: number; // 1-based row in the sheet (header is row 1)
  timestamp: string; // raw "Timestamp" cell
  email: string;
  firstName: string;
  lastName: string;
  orderNumber: string; // normalized — leading "#" stripped
  refundOrCredit: string | null; // RAW cell value (e.g. "Store credit for a
  // future order"); resolved from the "store credit" / "original form" /
  // "refund" substring column. Normalization to "original_method" |
  // "store_credit" happens in `domain/refund/api.ts` before sending to the
  // backend — the sheet entry stores the unmodified Google-Form answer so
  // drift (renamed answer choices) is visible in logs.
  // NOTE: `policyConfirmation` was REMOVED from this shape. The "refund
  // policy" column is no longer captured by the loader. The form gates
  // submission on it but no consumer requires it; per user direction we
  // simply ignore it.
  notes: string | null; // resolved from "anything else" or "note about" substring column
  transferRequest: string | null; // OPTIONAL — resolved from "transfer to
  // another day" or "sport, day, and division" substring column. No
  // consumer requires it; round-tripped to the backend on the validate
  // request body as `transferRequest?` for diagnostic logging only.
  statusCellValue: string | null; // raw value of the Status cell, or null if absent
  isProcessed: boolean; // derived: !!statusCellValue?.trim()
}

export interface RefundSheetData {
  url: string; // deep-link to the tab
  spreadsheetId: string;
  tabId: string;
  unprocessed: RefundSheetEntry[];
}
```

```typescript
// domain/refund/sheet_loader.ts  (functions; refund-specific column tokens)
import { findColumn } from "../../shared/google/columns.ts";
import type { RefundSheetData, RefundSheetEntry } from "./types.ts";

// Refund-specific column-token constants; passed to the generic findColumn().
export const REFUND_OR_CREDIT_TOKENS = [
  "store credit",
  "original form",
  "refund",
] as const;
// (other field-name → tokens lists declared here; see § "Column header resolution")

export async function fetchRefundRequests(
  env: Record<string, string>,
): Promise<RefundSheetData>;

export async function fetchRefundRequestsOrEmpty(
  env: Record<string, string>,
): Promise<RefundSheetData>;
```

```typescript
// shared/google/columns.ts  (generic; works on any sheet's header row)
/** Case-insensitive substring match against the header row. Returns the
 *  0-based column index, or `null` when no header contains the substring. */
export function findColumn(
  headers: string[],
  substring: string,
): number | null {
  const target = substring.toLowerCase();
  const idx = headers.findIndex((h) => h.toLowerCase().includes(target));
  return idx === -1 ? null : idx;
}
```

> No `isProcessedRow` helper. The check is inlined at every call site:
> `const isProcessed = !!row.statusCellValue?.trim();` (D26).

```typescript
// functions/send_request_for_eval.ts
export const SendRequestForEvalFunction = DefineFunction({
  callback_id: "send_request_for_eval",
  title: "Pick a refund request to evaluate",
  source_file: "functions/send_request_for_eval.ts",
  input_parameters: {
    properties: {
      interactivity: { type: Schema.slack.types.interactivity },
      channel_id: { type: Schema.slack.types.channel_id },
      slack_channel: { type: Schema.types.string }, // optional override; A2
    },
    required: ["interactivity", "channel_id"],
  },
  output_parameters: {
    properties: {
      processed_row_number: { type: Schema.types.string },
    },
    required: [],
  },
});
```

```typescript
// clients/bars_api/client.ts  (generic, refund-agnostic; one HTTP wrapper for any backend route)
//
// The BARS API client knows nothing about refunds. It exposes a small,
// parameterized surface (post<T> / get<T>) that any caller can use against
// any endpoint. Refund-specific typed wrappers live in
// `domain/refund/api.ts` (see below) — those are pure call-site
// convenience and contain no HTTP code.

export interface BarsApiPostArgs {
  endpoint: string; // path like "/refunds/validate"; joined with base URL inside the client
  params?: Record<string, string>; // query-string params
  body?: unknown; // JSON request body
  headers?: Record<string, string>; // additional headers; merged with defaults
}

export interface BarsApiGetArgs {
  endpoint: string;
  params?: Record<string, string>;
  headers?: Record<string, string>;
}

export interface BarsApiClient {
  post<T>(args: BarsApiPostArgs): Promise<T>;
  get<T>(args: BarsApiGetArgs): Promise<T>;
}

/**
 * Construct a BARS API client.
 *
 * Base URL is read from env `BARS_API_URL`. Default headers include:
 *   - `Content-Type: application/json`
 *   - `Accept: application/json`
 *   - `X-API-Key: <apiKey>` — sourced from env `BARS_API_KEY`. If unset,
 *     the header is omitted (sent as `null` / not included). The client
 *     does not fail on a missing key; the user will wire auth later. This
 *     no-op-when-null behavior is documented so deploys without a key
 *     surface as 401s from the backend rather than client-side throws.
 *
 * The client returns parsed JSON on 2xx and throws a descriptive error on
 * non-2xx (status code + response body excerpt + endpoint).
 */
export function makeBarsApiClient(env: Record<string, string>): BarsApiClient;
```

```typescript
// domain/refund/api.ts  (refund-domain typed call-site convenience layer; NO HTTP code)
//
// These types and helpers describe the shape of refund-specific calls
// against the generic BARS API client. They contain zero HTTP logic — the
// generic client owns transport, default headers, and error handling.
import type { BarsApiClient } from "../../clients/bars_api/client.ts";

export interface ValidateRefundRequest {
  orderNumber: string;
  requestedRefundTo: "original_method" | "store_credit";
  requesterEmail: string; // REQUIRED (was optional)
  requesterFirstName: string; // REQUIRED (was optional)
  requesterLastName: string; // REQUIRED (was optional)
  notes?: string | null; // OPTIONAL
  transferRequest?: string | null; // OPTIONAL — round-trips the sheet's "transfer to another day" cell
  sheetRowRef?: { spreadsheetId: string; tabId: string; rowNumber: number };
  isTest?: boolean; // OPTIONAL — defaults to false on the backend
  // REMOVED: `source` (always sheet — there is no other origin),
  //          `slackChannel` (channel routing is fully resolved on the Slack
  //          side; the backend never receives a channel hint),
  //          `policyConfirmation` (form gates submission on it; backend
  //          does not consume it).
}

// RefundRequestEval — the wire response from POST /refunds/validate.
// NOT a Pydantic model on the backend (D28 — Pydantic is reserved for
// incoming external request bodies). The backend constructs this dict
// manually; the Slack app reads field paths directly into its block builders.
export interface RefundRequestEval {
  ok: boolean;
  isValid: boolean; // replaces `validation.matched`
  validationErrors?: string[] | null; // replaces `validation.mismatches[]`; flat string[] only

  order: {
    id: string; // Shopify order GID
    number: string;
    customerName: string;
    email: string; // the order's customer email
    amountPaid: number; // total paid on the order, in dollars
    currency: string;
  };

  product: {
    // split out (was nested under `order` / `season`)
    id: string; // Shopify product GID
    url: string; // canonical product URL
    year: number;
    season: string; // "Winter" | "Spring" | "Summer" | "Fall"
    sport: string;
    day: string;
    division: string; // "WTNB+" | "Open" | ...
    week1Start: string | null; // ISO date — first session
    week2Start: string | null;
    week3Start: string | null;
    week4Start: string | null;
    week5Start: string | null;
  };

  estimate: {
    original: TierEstimate;
    storeCredit: TierEstimate;
  };
}

// (Legacy alias kept for IDE search; new code uses `RefundRequestEval`.)
// export type ValidateRefundResponse = RefundRequestEval;  // RENAMED — do not re-introduce.

export interface CreateRefundRequest {
  orderId: string; // REQUIRED — round-tripped from /validate
  productId: string; // REQUIRED — round-tripped from /validate
  refundTo: "original_method" | "store_credit"; // REQUIRED
  amount: number | null; // REQUIRED on refund; null when cancel-only
  cancel?: boolean; // OPTIONAL — defaults to false
  refund?: boolean; // OPTIONAL — defaults to false
  restockTo?: "veteran" | "early" | "general" | "waitlist" | "full"; // OPTIONAL — omit when no restock
  notify?: boolean; // OPTIONAL — defaults to false
  approvedBy: string; // REQUIRED — Slack user id
  isTest?: boolean; // OPTIONAL — defaults to false
  // REMOVED: `restock` (renamed to `restockTo`); options "none",
  //          "no_restock", "admin_hold" (gone — omit field instead).
}

export interface CreateRefundResponse {
  ok: boolean;
  cancel: { jobId: string; jobDone: boolean } | null;
  refund: {
    refundId: string;
    amount: number;
    currency: string;
    createdAt: string;
  } | null;
  errors: ShopifyUserError[];
}

// Thin typed wrappers — refund-specific *calls*, not refund-specific HTTP.
export const validateRefund = (
  client: BarsApiClient,
  body: ValidateRefundRequest,
) => client.post<RefundRequestEval>({ endpoint: "/refunds/validate", body });

export const executeRefund = (
  client: BarsApiClient,
  body: CreateRefundRequest,
) => client.post<CreateRefundResponse>({ endpoint: "/refunds/create", body });
```

#### Sheet read details

- Spreadsheet id and tab are declared in `config/workflows.ts` under
  `WORKFLOWS.refund.sheet`:
  - `spreadsheet_id`: env `SHEET_ID__REFUND_REQUESTS` (no default — required at deploy).
  - `tab_id`: env `TAB_ID__REFUND_REQUESTS` (no default — required at deploy).
  - `tab_name`: `Refund_Requests` (display label).
    Both env vars follow the workspace's `__` separator convention (matches
    `SLACK_CHANNEL__REFUNDS__DEFAULT`). See D24.
- The Google client lives at `slack-apps/registrations/shared/google/client.ts`.
  Reuse `getOrCreateGoogleClient(env)` and `client.getSpreadsheet(spreadsheetId, tab, columns)`.
- **Range to fetch:** `A1:N` (header + data, with headroom). The parser drops
  any row whose first cell is empty (existing client behavior).

##### Column header resolution (A5) — substring match, case-insensitive

The live `Refund_Requests` tab has these headers (order is **not** guaranteed):

```
Timestamp
Email Address
Please provide the Order Number you're requesting a refund for. … Please enter digits only, and only one order at a time …
Do you want a refund to your original form of payment, or store credit for a future order? …
Please confirm you have read our refund policy and agree to reduced refund amounts depending how far into the season we are
Anything else to note about this request?
First Name
Last Name
If looking to transfer to another day, please write what sport, day, and division (WTNB+ or Open) you would like to transfer to (and please make sure the other day is not sold out)
Status
```

Resolution rule: case-insensitive substring match against a unique, material
substring of each canonical header. Sub-agent must sanity-check uniqueness
against the live header list above (e.g. `email` is unique because no other
header contains the word "email"; `name` would NOT be unique because both
"First Name" and "Last Name" contain it).

| Field name (camelCase, canonical) | Candidate substring tokens (case-insensitive; tried in order, first match wins)                   |
| --------------------------------- | ------------------------------------------------------------------------------------------------- |
| `timestamp`                       | `timestamp`                                                                                       |
| `email`                           | `email`                                                                                           |
| `orderNumber`                     | `order number`                                                                                    |
| `refundOrCredit`                  | `store credit`, `original form`, `refund` (any one match wins; "store credit" is the most unique) |
| `notes`                           | `anything else`, `note about`                                                                     |
| `firstName`                       | `first name`                                                                                      |
| `lastName`                        | `last name`                                                                                       |
| `transferRequest`                 | `transfer to another day`, `sport, day, and division`                                             |
| `status`                          | `status` (whole-word preferred but case-insensitive substring is acceptable)                      |

**Match algorithm.** For each logical field, iterate the candidate substring
list in order; return the index of the first header whose lowercased text
contains the lowercased token. If no candidate matches, the loader logs a
warning and the corresponding entry field becomes `null` (the row still
appears in the picker; affected fields render blank).

The candidate-token map above is the **constants table** declared in
`domain/refund/sheet_loader.ts` (e.g.
`const REFUND_OR_CREDIT_TOKENS = ["store credit", "original form", "refund"] as const`),
so the matcher is parameterized by the field-name → tokens map rather than
hard-coded per-column. One sheet-row → domain-object parser, parameterized by
this map — not separate parsers per column.

Helper, in `shared/google/columns.ts` (refund-agnostic):

```typescript
function findColumn(headers: string[], substring: string): number | null {
  const target = substring.toLowerCase();
  const idx = headers.findIndex((h) => h.toLowerCase().includes(target));
  return idx === -1 ? null : idx;
}
```

If a non-`status` column is missing, the loader logs a warning and stores
`null` in the corresponding entry field — the operator sees the row but
fields render as blank in the picker.

If the `status` column is missing, the loader logs a warning and treats every
row as unprocessed (graceful degradation — the operator sees all rows until
the column exists). This behavior is internal; no diagnostic flag is
surfaced on `RefundSheetData` (D25).

##### refundOrCredit value normalization

The `refundOrCredit` column stores the **raw cell value** as written in the
sheet (a free-text answer to a Google Form question). Normalization to
`"original_method" | "store_credit"` happens in `domain/refund/api.ts` just
before posting to `/refunds/validate` (the typed call-site convenience layer
constructs the `ValidateRefundRequest` body) — not in the sheet loader. This
keeps `RefundSheetEntry` faithful to the spreadsheet so unexpected answer
strings are visible in logs.

The api-level normalizer:

- Any value containing "credit" (case-insensitive) → `"store_credit"`
- Anything else (including the typical "refund to original form of payment"
  answer) → `"original_method"`
- A null/empty raw value (header missing or cell empty) is treated as
  `"original_method"` and a warning is logged.

#### Unprocessed-entry detection

**Single rule:** a row is unprocessed iff its `Status` cell is empty when
trimmed. Anything non-empty (any character at all) means processed and the
row is excluded from the picker. The check is **inlined** at every call site
— there is no `isProcessedRow` helper (D26):

```typescript
const isProcessed = !!row.statusCellValue?.trim();
```

**Green-highlight detection is dropped permanently.** No
`effectiveFormat.backgroundColor` lookup, no Sheets formatting API call, no
`isGreenBackground` / `isRowProcessed` helpers, no `sheet_format.ts` file, no
`REFUND_SHEET_PROCESSED_DETECTOR` env var.

If the sheet is missing the `Status` column entirely, the loader logs a warning
and treats every row as unprocessed (graceful degradation — the operator sees
all rows until the column exists). This behavior is internal; no diagnostic
flag is surfaced on `RefundSheetData` (D25). Status writes (Stage 5) populate
the cell once the row is acted on; until then every row reads as unprocessed
(operator can also manually clear cells if needed).

#### Modal reuse plan

Both modals (the picker and the approval modal) are now **generic, reusable
block builders** at `slack-apps/registrations/views/_shared/`. Refund-specific
behavior lives in thin callers that pass refund-shaped configuration. This
matches the same "generic, parameterized" principle as the BARS API client
(see D23).

**Picker modal — `views/_shared/picker_modal.ts`** (generic; refund flow
uses it directly without a refund-specific wrapper).

```typescript
// views/_shared/picker_modal.ts
import type { SlackBlock, SlackView } from "../../shared/slack/types.ts";

export interface PickerModalArgs<T> {
  callbackId: string;
  title: string;
  submitLabel: string;
  closeLabel: string;
  items: T[];
  formatItem: (item: T) => { title: string; context?: string[] };
  getItemId: (item: T) => string | number;
  pageSize?: number; // default 10
  currentOffset?: number;
  selectedItemId?: string | number | null;
  extraInputBlocks?: SlackBlock[]; // for the "post to channel" override field, etc.
  metadata?: Record<string, unknown>; // serialized into private_metadata
}

export function pickerModal<T>(args: PickerModalArgs<T>): SlackView;
```

The picker has **zero refund domain knowledge** — no `RefundSheetEntry`
references in `views/_shared/picker_modal.ts`. The refund-specific picker
usage lives inside the calling function (`functions/send_request_for_eval.ts`):
it imports `pickerModal`, hands it a refund-shaped `items` array, and
provides a refund-specific `formatItem` (e.g.
`(row) => ({ title: \`${row.firstName} ${row.lastName} • ${row.orderNumber}\`, context: [row.timestamp] })`).

> **Implementation note for the sub-agent.** The existing
> `slack-apps/registrations/shared/slack/list_modal.ts` may already do most
> of this. The sub-agent should READ that file first and either (a) extend
> it in place to take the parameterized `formatItem` / `getItemId`
> callbacks above, or (b) create a sibling `views/_shared/picker_modal.ts`
> that delegates to it. Document the choice in the Stage 1 PR description.

**Approval modal — `views/_shared/approve_modal.ts`** (generic block
builders; the existing `views/refund/approve_modal.ts` becomes a thin
caller).

```typescript
// views/_shared/approve_modal.ts
export interface ApproveModalArgs<TMeta extends Record<string, unknown>> {
  callbackId: string;
  title: string;
  headerBlocks: SlackBlock[]; // caller provides the order/customer summary
  actionOptions: Array<{ value: string; label: string }>; // e.g. [{value:"cancel_refund", label:"Cancel + Refund"}, ...]
  amountInput?: {
    default: number;
    min: number;
    max: number;
    required: boolean;
  };
  restockOptions?: Array<{ value: string; label: string }>;
  notifyToggle?: { default: boolean; label: string };
  metadata: TMeta;
}

export function approveModal<TMeta extends Record<string, unknown>>(
  args: ApproveModalArgs<TMeta>,
): SlackView;
```

The generic builder has **zero refund domain knowledge** — all refund-specific
labels, defaults, and action values are passed in by the caller. The existing
`slack-apps/registrations/views/refund/approve_modal.ts` becomes a thin
caller that imports `approveModal` and supplies the refund config:

```typescript
// views/refund/approve_modal.ts (UPDATE — thin caller)
import { approveModal } from "../_shared/approve_modal.ts";
import type { ApproveModalMeta } from "../../domain/refund/types.ts";

// 1-line constant rename happens inside this thin caller, not the generic builder.
export const REFUND_APPROVAL_MODAL_CALLBACK_ID = "refund_approval_modal";

export function buildRefundApproveModal(args: BuildRefundApproveModalArgs) {
  return approveModal<ApproveModalMeta>({
    callbackId: REFUND_APPROVAL_MODAL_CALLBACK_ID,
    title: "Approve Refund",
    headerBlocks: buildRefundHeaderBlocks(args.order, args.customer),
    actionOptions: [
      { value: "cancel_refund", label: "Cancel + Refund" },
      { value: "cancel_only", label: "Cancel only" },
      { value: "refund_only", label: "Refund only" },
    ],
    amountInput: {
      default: args.estimate.original.amount,
      min: 0,
      max: args.order.total,
      required: true,
    },
    restockOptions: REFUND_RESTOCK_OPTIONS,
    notifyToggle: { default: true, label: "Notify customer" },
    metadata: args.meta,
  });
}
```

**1-line constant rename inside the thin caller.** The pre-existing
`APPROVE_MODAL_CALLBACK_ID = "approve_refund_modal"` constant in
`views/refund/approve_modal.ts` becomes
`REFUND_APPROVAL_MODAL_CALLBACK_ID = "refund_approval_modal"`. The rename
lives in the thin caller; the generic builder takes the callback id as an
argument and stays refund-agnostic.

Stage 1 adds:

1. A **picker modal usage** that calls `pickerModal({ items: unprocessedRows, formatItem, ... })`
   with one radio button per row showing
   `{firstName} {lastName} • {orderNumber} • {timestamp}`, paginated. Reuses
   `shared/slack/modal_state.ts`. Includes an optional
   "post review card to channel" plain-text input pre-filled from the
   slash command's `channel_id` via the generic `extraInputBlocks` arg.
2. A **handler** (`functions/send_request_for_eval.ts`) that:
   - On slash command: opens the picker modal (via the generic builder).
   - On picker submit: calls `validateRefund(barsApi, body)` (the typed
     wrapper from `domain/refund/api.ts`), passing `slackChannel`
     resolved from the picker's "post to channel" input. Then **pushes**
     the existing refund approval modal (`refund_approval_modal`) pre-filled
     from the validate response (`response_action: "push"` — same pattern
     as `handle_waitlist_actions.ts:CONFIRM_CALLBACK_ID`).
   - On approval-modal submit: hands off to the existing
     `handleApproveModalSubmit` orchestrator (already in
     `domain/refund/orchestrator.ts`), which calls `executeRefund(barsApi, body)`.
     Stage 1 forces the BARS-API path by ensuring `BARS_API_URL` is set;
     the orchestrator already handles this via `barsApiConfigured()`.
3. **No duplication of modal/orchestrator code.** All new code is in
   `domain/refund/types.ts`, `domain/refund/sheet_loader.ts`,
   `domain/refund/api.ts`, `clients/bars_api/client.ts`,
   `views/_shared/picker_modal.ts`, `views/_shared/approve_modal.ts`,
   `shared/google/columns.ts`, `functions/send_request_for_eval.ts`,
   `triggers/start_refund_eval.ts`, `workflows/validate_refund_request.ts`,
   plus the thin-caller update inside `views/refund/approve_modal.ts`.

#### Channel routing

**Precedence (highest first), enforced in the slack-side handler:**

1. `slackChannel` field on the inbound request (operator-supplied via the
   picker modal's "post to channel" input). The backend echoes whatever
   value Slack sent — Slack is the source of truth for channel routing.
2. `SLACK_CHANNEL__REFUNDS__DEFAULT` env var (the canonical name; double
   underscores match the workspace convention). The user sets this value
   later — design must not require an actual override at deploy time.
3. Hardcoded fallback `"#joe-test"`.

Inline form: `slackChannel ?? Deno.env.get("SLACK_CHANNEL__REFUNDS__DEFAULT") ?? "#joe-test"`.

The override is read inside the slack-side handler (`functions/send_request_for_eval.ts`),
not on the backend. **The backend's `/refunds/validate` request body does NOT
accept any channel field** — channel routing is fully resolved on the Slack
side using the precedence chain above; the backend never receives a channel
hint.

`config/workflows.ts` declares `SLACK_CHANNEL__REFUNDS__DEFAULT` as a **new**
env var (additional to, not replacing, the existing `REFUND_TEST_CHANNEL` and
`REFUND_REVIEW_CHANNEL`). The two existing vars continue to drive the existing
webhook flow's channel routing untouched; only the new `eval-refund-request`
slash-command flow reads `SLACK_CHANNEL__REFUNDS__DEFAULT`.

```typescript
// config/workflows.ts (UPDATED)
WORKFLOWS.refund.channels = {
  source: "static",
  default: envOr("SLACK_CHANNEL__REFUNDS__DEFAULT", "#joe-test"),
};
```

```typescript
// shared/slack/channel.ts — channel-resolver helper
export function resolveRefundChannel(args: {
  requested: string | null; // from request.slackChannel (picker override)
  env: Record<string, string>;
}): string {
  // slackChannel ?? Deno.env.get("SLACK_CHANNEL__REFUNDS__DEFAULT") ?? "#joe-test"
  return (
    args.requested?.trim() ||
    args.env.SLACK_CHANNEL__REFUNDS__DEFAULT ||
    "#joe-test"
  );
}
```

The slash-command picker pre-fills the "post to channel" field from the
slash command's invoking `channel_id`, so the default UX is "post here".
Operator can clear it (→ env default `SLACK_CHANNEL__REFUNDS__DEFAULT` →
hardcoded `"#joe-test"`) or paste a different channel.

> **Existing env vars left untouched.** `REFUND_TEST_CHANNEL` and
> `REFUND_REVIEW_CHANNEL` are NOT read by the new `eval-refund-request` flow
> — the existing webhook-driven refund-evaluation flow continues to use them
> as-is. The new flow reads only `SLACK_CHANNEL__REFUNDS__DEFAULT`.

#### Slash command + trigger

```typescript
// triggers/start_refund_eval.ts
import { TriggerTypes, TriggerContextData } from "deno-slack-api/mod.ts";
import ValidateRefundRequestWorkflow from "../workflows/validate_refund_request.ts";

export default {
  type: TriggerTypes.Shortcut,
  name: "Evaluate Refund Request", // display copy unchanged
  description:
    "Pick an unprocessed refund request from the sheet and evaluate it",
  workflow: `#/workflows/${ValidateRefundRequestWorkflow.definition.callback_id}`,
  inputs: {
    interactivity: { value: TriggerContextData.Shortcut.interactivity },
    channel_id: { value: TriggerContextData.Shortcut.channel_id },
  },
};
```

```typescript
// workflows/validate_refund_request.ts
import { DefineWorkflow, Schema } from "deno-slack-sdk/mod.ts";
import { SendRequestForEvalFunction } from "../functions/send_request_for_eval.ts";

const ValidateRefundRequestWorkflow = DefineWorkflow({
  callback_id: "validate_refund_request",
  title: "Evaluate Refund Request",
  input_parameters: {
    properties: {
      interactivity: { type: Schema.slack.types.interactivity },
      channel_id: { type: Schema.slack.types.channel_id },
      slack_channel: { type: Schema.types.string }, // optional override
    },
    required: ["interactivity", "channel_id"],
  },
});

ValidateRefundRequestWorkflow.addStep(SendRequestForEvalFunction, {
  interactivity: ValidateRefundRequestWorkflow.inputs.interactivity,
  channel_id: ValidateRefundRequestWorkflow.inputs.channel_id,
  slack_channel: ValidateRefundRequestWorkflow.inputs.slack_channel,
});

export default ValidateRefundRequestWorkflow;
```

Manifest update (only delta to existing manifest):

```typescript
// manifest.ts — add to workflows: [...]
import ValidateRefundRequestWorkflow from "./workflows/validate_refund_request.ts";
// ... existing imports + workflows
workflows: [
  // existing...
  ValidateRefundRequestWorkflow,
],
// botScopes already includes "commands"
```

The slash command itself is registered via the Slack CLI (`slack triggers create`)
pointing at `triggers/start_refund_eval.ts`. Command name: **`/eval-refund-request`**.
Documented in the README update.

### 1b — Modal block IDs + exact contracts

#### Picker primitives (generic, in `views/_shared/picker_modal.ts`) + per-flow input ids

The picker block-builder itself is **generic and parameterized** — every id
it emits is derived from the caller's `callbackId` argument. There are no
refund-specific constants in `views/_shared/picker_modal.ts`. (D29.)

```typescript
// views/_shared/picker_modal.ts (generic primitives — NO refund domain)
export const PICKER_ENTRIES_PER_PAGE_DEFAULT = 10;

export function pickerActionIds(callbackId: string) {
  return {
    radioPrefix: `${callbackId}__radio_`, // page index appended at use site
    nextPage: `${callbackId}__next_page`,
    prevPage: `${callbackId}__prev_page`,
  };
}
```

The refund flow's caller passes `callbackId: "refund_pick_row"` and consumes
`pickerActionIds("refund_pick_row")` to render and bind action handlers — no
refund-specific picker constants exist outside the calling function.

**Per-flow input blocks (test toggle, post-to-channel) live alongside the
calling function**, NOT in `views/_shared/`. They are constructed by the
refund flow and passed to `pickerModal()` via the existing `extraInputBlocks`
parameter. The block / action ids stay co-located with the caller:

```typescript
// functions/send_request_for_eval.ts (refund-flow per-flow constants)
export const PICK_ROW_CALLBACK_ID = "refund_pick_row";

// Per-flow input blocks supplied to pickerModal() via `extraInputBlocks`.
// These are NOT picker primitives — they are concerns of THIS flow only.
export const ACTION_TOGGLE_TEST_MODE = "refund_toggle_test";
export const BLOCK_POST_TO_CHANNEL = "refund_post_to_channel";
export const ACTION_POST_TO_CHANNEL = "refund_post_to_channel_input";

export interface PickRowModalState {
  off: number; // pagination offset
  selectedRowNumber: number | null; // single-select
  isTest: boolean;
  ch: string; // channel_id from slash command (default for "post to")
  slackChannel: string | null; // operator-overridden post-target; round-trips
  // into ApproveModalMeta on submit so the final-message chat.postMessage
  // lands in the same channel that received the review card. Falls back to
  // env SLACK_CHANNEL__REFUNDS__DEFAULT (= "#joe-test") when null/empty.
}
```

#### Approval modal — `refund_approval_modal` (thin caller in `views/refund/approve_modal.ts`)

After Stage 1, `views/refund/approve_modal.ts` is a **thin caller** that
delegates to the generic `views/_shared/approve_modal.ts` block builder
(D23). All refund-specific labels, defaults, and action values are passed
in by the caller; the generic builder has no refund domain knowledge.

- Constant: `REFUND_APPROVAL_MODAL_CALLBACK_ID = "refund_approval_modal"`
  (renamed from `APPROVE_MODAL_CALLBACK_ID = "approve_refund_modal"`). The
  rename happens **inside the thin caller**, not the generic builder.
- Block IDs: `ACTION_BLOCK_ID`, `AMOUNT_BLOCK_ID`, `RESTOCK_BLOCK_ID`, `NOTIFY_BLOCK_ID`
- Action IDs: `ACTION_ACTION_ID`, `AMOUNT_ACTION_ID`, `RESTOCK_ACTION_ID`, `NOTIFY_ACTION_ID`
- The modal's `private_metadata` carries an `ApproveModalMeta` (`{channel, message_ts}`).
  Stage 1 extends the meta with three small fields so the approval-modal submit
  handler can pass back to `/refunds/create` without a Shopify re-fetch:
  - `orderId: string` (Shopify order GID — ~40 chars)
  - `productId: string` (Shopify product GID for the refunded line item — ~40 chars)
  - `slackChannel?: string` (operator-supplied channel override that round-trips
    from the picker modal's `private_metadata` so the final-confirmation
    `chat.postMessage` lands in the same channel that received the review card)

  All three round-trip cleanly inside Slack `private_metadata`'s 3 KB ceiling. No
  opaque "remaining metadata" blob is round-tripped — the small field set is
  sufficient because the backend re-derives everything else it needs by
  refetching the order on `/refunds/create`. The 3 KB concern is dropped.

#### Endpoint contracts

```http
POST /refunds/validate
Content-Type: application/json

{
  "orderNumber": "48957",
  "requestedRefundTo": "original_method",
  "requesterEmail": "alice@example.com",
  "requesterFirstName": "Alice",
  "requesterLastName": "Doe",
  "notes": "Couldn't make it to season",
  "transferRequest": null,
  "sheetRowRef": {
    "spreadsheetId": "11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw",
    "tabId": "1435845892",
    "rowNumber": 42
  },
  "isTest": true
}
// NOTE: NO `source`, NO `slackChannel`, NO `policyConfirmation`. The
// requesterEmail / requesterFirstName / requesterLastName fields are now
// REQUIRED. `isTest` is OPTIONAL on the wire — Slack handler omits it when
// not in test mode; the backend Pydantic model defaults to false.

→ 200 OK   ── RefundRequestEval (plain dict / TypedDict — NOT Pydantic; D28)
{
  "ok": true,
  "isValid": true,
  "validationErrors": null,

  "order": {
    "id":           "gid://shopify/Order/5234567890",
    "number":       "#48957",
    "customerName": "Alice Doe",
    "email":        "alice@example.com",
    "amountPaid":   87.50,
    "currency":     "USD"
  },

  "product": {
    "id":         "gid://shopify/Product/7590021333086",
    "url":        "https://bigapplerecsports.com/products/winter-2025-thursday-open-volleyball",
    "year":       2025,
    "season":     "Winter",
    "sport":      "Volleyball",
    "day":        "Thursday",
    "division":   "Open",
    "week1Start": "2025-01-15",
    "week2Start": "2025-01-22",
    "week3Start": "2025-01-29",
    "week4Start": "2025-02-05",
    "week5Start": "2025-02-12"
  },

  "estimate": {
    "original":    { "amount": 87.50, "percentage": 100, "tierLabel": "before week 1 started" },
    "storeCredit": { "amount": 95.00, "percentage": 110, "tierLabel": "before week 1 started" }
  }
}
```

`order.id` and `product.id` are the two GIDs the Slack handler reads into the
picker modal's `private_metadata` and the `ApproveModalMeta` (`{orderId, productId}`)
for the round-trip into `/refunds/create`. Both are short Shopify GID strings
(~40 chars each) — well within Slack `private_metadata`'s 3 KB ceiling.

`POST /refunds/create` and `DELETE /orders/{id}` are owned by Stages 5/6.
Stage 1 only needs to call them through the existing `executeActionRequest`
in `domain/refund/action_requests.ts` — no new client code.

#### Env vars (Stage 1 only)

| Var                               | Default                     | Owner    | Notes                                                                                                                                                                    |
| --------------------------------- | --------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `SLACK_CHANNEL__REFUNDS__DEFAULT` | `#joe-test`                 | **new**  | Default refund-review channel for the new `/eval-refund-request` flow; canonical name with `__` separators. **The only env var the new flow reads** for channel routing. |
| `SHEET_ID__REFUND_REQUESTS`       | (none — required at deploy) | **new**  | Spreadsheet ID of the `Refund_Requests` sheet (replaces the prior hardcoded default + `REFUND_SHEET_ID` env var). Double-underscore convention.                          |
| `TAB_ID__REFUND_REQUESTS`         | (none — required at deploy) | **new**  | Tab id within the `Refund_Requests` spreadsheet (replaces the prior hardcoded default of `1435845892`). Double-underscore convention.                                    |
| `BARS_API_URL`                    | (unset)                     | existing | Required to route `/refunds/validate` to backend instead of Lambda. Read by `clients/bars_api/client.ts`.                                                                |
| `BARS_API_KEY`                    | (unset)                     | **new**  | Optional `X-API-Key` for the BARS API client. If unset, the header is omitted (sent as `null` / not included). The user wires real auth later (D22).                     |
| `ENV`                             | `test`                      | existing | `prod` flips to live channel + non-dry-run execution                                                                                                                     |

> **Removed from prior draft:** `REFUND_TEST_CHANNEL` (replaced by
> `SLACK_CHANNEL__REFUNDS__DEFAULT`); `REFUND_SHEET_PROCESSED_DETECTOR`
> (highlight-detection mode dropped entirely; Status column is the only
> rule); `REFUND_SHEET_ID` (replaced by `SHEET_ID__REFUND_REQUESTS`).
>
> **Left untouched (not read by the new flow):** `REFUND_REVIEW_CHANNEL` and
> `REFUND_TEST_CHANNEL`. The existing webhook-driven refund-evaluation flow
> continues to read these — the new flow reads only
> `SLACK_CHANNEL__REFUNDS__DEFAULT`.

`config/workflows.ts` references the new sheet env vars: `WORKFLOWS.refund.sheet`
now reads `spreadsheet_id` from `SHEET_ID__REFUND_REQUESTS` and `tab_id` from
`TAB_ID__REFUND_REQUESTS` (no defaults — fail fast at deploy if either is unset).

### 1c — Smoke checks + tests (deferred)

#### Smoke checks (manual, post-deploy to `#joe-test`)

1. Operator runs `/eval-refund-request` in `#joe-test` → picker modal opens with N
   unprocessed rows (only rows where the `Status` cell is empty).
2. Operator picks a row → review card posts to `#joe-test`.
3. Operator clicks **Approve** → `refund_approval_modal` opens pre-filled
   with the validated estimate.
4. Operator submits → backend receives `POST /refunds/create` with `orderId`
   - `productId` round-tripped from the validate response (or executes the
     existing Lambda fallback during Stage 1, before Stage 5 lands).
5. Final confirmation message posts to `#joe-test`. (Stage 5/7 wire this
   end-to-end; Stage 1 only verifies up through the existing orchestrator's
   behavior.)

#### Tests planned (deferred — file names only)

All tests are deferred to a later stage. Build these in a later stage:

- `slack-apps/registrations/tests/clients/bars_api/client_test.ts`
- `slack-apps/registrations/tests/domain/refund/sheet_loader_test.ts`
- `slack-apps/registrations/tests/domain/refund/api_test.ts`
- `slack-apps/registrations/tests/views/_shared/picker_modal_test.ts`
- `slack-apps/registrations/tests/views/refund/approve_modal_test.ts`
- `slack-apps/registrations/tests/functions/send_request_for_eval_test.ts`

---

## Stage 2 — Refund estimate consolidation [DETAILED]

> Goal: a single `EstimateService.compute_estimate(request)` method backing
> `POST /refunds/validate`, with all legacy estimate implementations either
> migrated to call it or deleted. Pure-math tier resolution stays in
> `backend/modules/refunds/refund_calculator.py` (the canonical estimator —
> verified at lines 314–368, signature
> `estimate_refund_due(season: SeasonDates, total_paid: float, tier_kind: EstimateTierKind, submitted_at: datetime | None = None) -> RefundResult`).
> Stage 2 wraps this estimator in a service-layer authority that pulls the
> Shopify order, derives the season, and emits both ladders in a single
> response.

### 2.1 — Inventory of existing implementations (no rediscovery — reuse)

| Path                                                                                                         | Signature / shape                                                                 | Disposition                                                                                                                                                                              |
| ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/modules/refunds/refund_calculator.py:343` `estimate_refund_due(season, total_paid, ...)`            | Canonical pure-math tier resolver. `SeasonDates` / `RefundTier` / `RefundResult`. | **KEEP.** Imported by `EstimateService.compute_estimate(...)`. Existing tests at `backend/tests/modules/refunds/test_refund_calculator.py` cover it.                                     |
| `backend/modules/refunds/calculate_refund_due.py:12` `calculate_refund_due(order_data, refund_type, ...)`    | Order-data-typed wrapper.                                                         | **MIGRATE then DELETE.** All callers (`OrdersService.calculate_refund_due` + tests) re-pointed at `EstimateService.compute_estimate(...)`.                                               |
| `backend/modules/refunds/app/calculate_refund_due.py:12` `calculate_refund_due(...)`                         | Duplicate of the above (different package path).                                  | **DELETE.** Re-export of the same logic.                                                                                                                                                 |
| `backend/modules/orders/services/orders_service.py:21` `OrdersService.calculate_refund_due(order_data, ...)` | Service-method form, takes order_data dict.                                       | **MIGRATE.** Replace body with `EstimateService.compute_estimate(...)` call; eventually delete the method.                                                                               |
| `backend/modules/orders/services/orders_service_old.py:335` `calculate_refund_due(...)`                      | Older copy.                                                                       | **DELETE** (the entire `_old.py` file is dead code).                                                                                                                                     |
| `backend/legacy/registrations/services/refunds_service.py:97` `refund_estimate_breakdown(...)`               | Legacy "breakdown" form returning labeled tiers.                                  | **MIGRATE.** Re-point legacy callers at `EstimateService.compute_estimate(...)`. **Gating dependency** — see 2.g.                                                                        |
| `backend/legacy/registrations/utils/refund_calculator.py:201` `estimate_refund_due(...)`                     | Twin of the canonical version.                                                    | **DELETE** after `backend/legacy/registrations/services/refunds_service.py` is migrated. Order matters — see 2.g.                                                                        |
| `backend/legacy/shared/date_utils.py:209` `calculate_refund_amount(...)`                                     | Date-math heart of the estimate (pre-`refund_calculator.py`).                     | **DELETE.** Already superseded by `refund_calculator.py`. The `parse_season_start_date` / `parse_off_dates` / `weeks_into_season` helpers extract to `backend/utils/dates.py` (see 2.d). |

### 2.a — Module structure (concrete)

Target layout under `backend/modules/refunds/`:

```
backend/modules/refunds/
├── __init__.py
├── refund_calculator.py             # existing, KEEP — pure tier-math
├── controllers/
│   ├── __init__.py
│   └── refunds_controller.py        # NEW — thin FastAPI handlers
├── services/
│   ├── __init__.py
│   ├── estimate_service.py          # NEW — single estimate authority (Stage 2)
│   └── (Stage 3 adds shopify_refund_service.py;
│         Stage 5 wires POST /refunds/create directly through the controller —
│         NO orchestrator service. See D30.)
├── models/
│   ├── __init__.py
│   ├── estimate.py                  # NEW — EstimateRequest (internal value object), TierEstimate / OrderInfo / ProductInfo / EstimateBlock / RefundRequestEval (TypedDicts; D28)
│   └── refund_request.py            # NEW — RefundRequest model (shared with /create in Stage 5)
└── tests/
    ├── __init__.py
    ├── test_estimate_service.py     # NEW — Stage 2 service tests
    ├── test_estimate_controller.py  # NEW — Stage 2 controller tests
    └── test_refund_dates.py         # NEW — date-utility extraction tests (see 2.d)
```

### 2.b — Pydantic v2 models

```python
# backend/modules/refunds/models/estimate.py
#
# Pydantic boundary in this module:
#   - `EstimateRequest` is an INTERNAL Python value object built by the
#     controller from the `RefundRequest` (incoming) body. It can stay as a
#     Pydantic model OR be a plain `@dataclass` — sub-agent's choice. It is
#     NOT a wire shape. Per D28, internal value objects don't strictly need
#     Pydantic; either is acceptable.
#   - `RefundEstimate` is an INTERNAL value object returned by the estimate
#     authority and embedded in `RefundRequestEval`. It is a TypedDict (or
#     plain dataclass) — NOT Pydantic — because the controller serializes it
#     into the outgoing dict. (D28.)
#   - `EstimateResponse` is REMOVED as a Pydantic model. The previous
#     "EstimateBreakdown / EstimateResponse" wire shape is replaced by
#     `RefundRequestEval` (see below), constructed manually in the controller.

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional, TypedDict
from dataclasses import dataclass


class TierEstimate(TypedDict):
    """One ladder's worth of tier output. Embedded into RefundRequestEval.estimate.
    Plain TypedDict — NOT Pydantic (D28)."""

    amount: float                  # post-percentage amount, USD
    percentage: int                # tier percentage (e.g. 95)
    tierLabel: str                 # human-readable, e.g. "before week 1 started"
    appliedProcessingFee: float    # 0 for store_credit; 5% for refund-to-original (post-week-0)
    notes: List[str]               # free-form annotations (e.g. "no_payment_made")


@dataclass
class EstimateRequest:
    """Inputs to the estimate authority. Internal value object — NOT a wire
    shape. The controller builds this from `RefundRequest`. May be a
    `@dataclass` since it doesn't cross the network boundary."""

    order_number: str                              # "#48957" or "48957" — controller normalizes
    requested_refund_to: Literal["original_method", "store_credit"]
    submitted_at: datetime                         # when the request was filed (sheet timestamp)
    order_id: Optional[str] = None                 # Shopify order GID (preferred when known)
    product_id: Optional[str] = None               # Shopify product GID (optional; service derives if absent)
    season_start_date: Optional[date] = None       # OPTIONAL override; bypasses HTML parsing
    notes: Optional[str] = None                    # operator-supplied notes (advisory)


# RefundRequestEval — the OUTGOING wire shape served by POST /refunds/validate.
# Plain TypedDict — NOT a Pydantic model (D28). The FastAPI controller
# constructs it manually and returns it as a dict. Field names match the
# wire JSON exactly (camelCase) — there is no alias indirection because
# nothing validates this shape on the server side.

class OrderInfo(TypedDict):
    id: str             # Shopify order GID
    number: str
    customerName: str
    email: str          # the order's customer email
    amountPaid: float   # total paid on the order, in dollars
    currency: str


class ProductInfo(TypedDict):
    """Split-out product information. Stage 2's EstimateService is responsible
    for extracting these fields — see § 2.c for the extraction strategy."""
    id: str             # Shopify product GID
    url: str            # canonical product URL
    year: int
    season: str         # "Winter" | "Spring" | "Summer" | "Fall"
    sport: str
    day: str
    division: str       # "WTNB+" | "Open" | ...
    week1Start: Optional[str]  # ISO date — first session
    week2Start: Optional[str]
    week3Start: Optional[str]
    week4Start: Optional[str]
    week5Start: Optional[str]


class EstimateBlock(TypedDict):
    original: TierEstimate
    storeCredit: TierEstimate


class RefundRequestEval(TypedDict, total=False):
    """The OUTGOING wire response from POST /refunds/validate. Plain
    TypedDict — NOT Pydantic (D28).

    `total=False` lets `validationErrors` be omitted entirely on the happy
    path; required keys (ok, isValid, order, product, estimate) are always
    populated by the controller."""

    ok: bool
    isValid: bool                       # replaces validation.matched
    validationErrors: Optional[List[str]]  # replaces validation.mismatches[]; flat string[] only

    order: OrderInfo
    product: ProductInfo
    estimate: EstimateBlock
```

```python
# backend/modules/refunds/models/refund_request.py
# Pydantic v2 model — used for the INCOMING /refunds/validate request body
# only (D28: Pydantic is reserved for incoming external objects). Outgoing
# responses are constructed as plain dicts / TypedDicts in the controller.
from typing import Literal, Optional
from pydantic import BaseModel, Field


class SheetRowRef(BaseModel):
    spreadsheet_id: str
    tab_id: str
    row_number: int


class RefundRequest(BaseModel):
    """The full validate-side request body sent by the Slack handler.

    Field requirements (post-D28 wire-shape change):
      - REQUIRED: order_number, requested_refund_to, requester_email,
        requester_first_name, requester_last_name.
      - OPTIONAL: notes, transfer_request, sheet_row_ref, is_test (defaults
        to False; Slack handler omits it when not in test mode).

    REMOVED fields:
      - `source` (the request always originates from a sheet — there is no
        other source).
      - `slack_channel` (channel routing is fully resolved on the Slack side
        using `request override → SLACK_CHANNEL__REFUNDS__DEFAULT → "#joe-test"`;
        the backend never receives a channel hint).
      - `policy_confirmation` (the form gates submission on it; the backend
        does not consume it; the sheet loader still captures the cell value
        for diagnostic logging only — it is NOT sent on this request body).
    """

    order_number:         str                                   = Field(..., alias="orderNumber")
    requested_refund_to:  Literal["original_method", "store_credit"] = Field(..., alias="requestedRefundTo")
    requester_email:      str                                   = Field(..., alias="requesterEmail")
    requester_first_name: str                                   = Field(..., alias="requesterFirstName")
    requester_last_name:  str                                   = Field(..., alias="requesterLastName")
    notes:                Optional[str]                          = None
    transfer_request:     Optional[str]                          = Field(None, alias="transferRequest")
    sheet_row_ref:        Optional[SheetRowRef]                  = Field(None, alias="sheetRowRef")
    is_test:              bool                                   = Field(False, alias="isTest")

    model_config = {"populate_by_name": True}

    def to_estimate_request(self, *, submitted_at, season_start_date=None) -> "EstimateRequest":
        from .estimate import EstimateRequest
        return EstimateRequest(
            order_number=self.order_number,
            requested_refund_to=self.requested_refund_to,
            submitted_at=submitted_at,
            season_start_date=season_start_date,
            notes=self.notes,
        )
```

### 2.c — `EstimateService` — signatures + algorithm pseudocode

```python
# backend/modules/refunds/services/estimate_service.py
from datetime import datetime
from decimal import Decimal
from typing import Optional

from box import Box
from modules.refunds.models.estimate import (
    EstimateRequest, RefundRequestEval, OrderInfo, ProductInfo,
    EstimateBlock, TierEstimate,
)
from modules.refunds.refund_calculator import (
    SeasonDates, EstimateTierKind, RefundResult, estimate_refund_due,
)


class EstimateService:
    """Single estimate authority for the refund-cancel workflow.

    Wraps the pure-math tier resolver in `refund_calculator.py` with a
    Shopify-order lookup + season derivation + dual-ladder evaluation.
    Every backend caller of refund-estimate logic (FastAPI controller, legacy
    callsites being migrated) goes through this service.

    Returns a fully-built `RefundRequestEval` dict (the wire shape served by
    POST /refunds/validate) — NOT a Pydantic model (D28). The controller
    returns the dict directly with FastAPI's `response_model` set to `dict`
    or omitted entirely.
    """

    def __init__(self, shopify_refund_service=None):
        # Stage 3's ShopifyRefundService is injected here; lazy-construct from
        # env when not provided so unit tests can pass a fake.
        self._shopify_refund_service = shopify_refund_service

    @property
    def shopify_refund_service(self):
        if self._shopify_refund_service is None:
            from modules.refunds.services.shopify_refund_service import ShopifyRefundService
            self._shopify_refund_service = ShopifyRefundService()
        return self._shopify_refund_service

    async def compute_estimate(self, req: EstimateRequest) -> RefundRequestEval:
        """Compute both refund ladders + product/order metadata for a single
        order, and return the wire-shaped `RefundRequestEval` dict.

        Preconditions:
          - `req.order_number` is a non-empty string (controller validates).
          - `req.submitted_at` is timezone-aware (controller defaults to now-UTC).

        Postconditions:
          - Returns a `RefundRequestEval` dict with `ok`, `isValid`, `order`,
            `product`, and `estimate` populated. `validationErrors` is
            absent on the happy path; populated as a flat `list[str]` when
            `isValid` is False.
          - Calls `refund_calculator.estimate_refund_due` exactly twice (once
            per `EstimateTierKind`).
          - Issues at most one Shopify call (`fetch_order_for_refund`).

        Raises:
          - `OrderNotFoundError` when no order matches `req.order_number`.
        """
        order = await self.shopify_refund_service.fetch_order_for_refund(
            order_id=req.order_id,
            order_number=req.order_number,
        )
        season = self._resolve_season(order, override=req.season_start_date)
        total_paid = self._extract_total_paid(order)
        return {
            "ok": True,
            "isValid": True,
            "order": self._build_order_info(order, total_paid),
            "product": self._build_product_info(order, season),
            "estimate": {
                "original":    self._apply_tier(season, total_paid, "original_method", req.submitted_at),
                "storeCredit": self._apply_tier(season, total_paid, "store_credit",    req.submitted_at),
            },
        }

    # ── Field-extraction strategy (RefundRequestEval.product) ─────────────
    #
    # `product` is built from the Shopify order's first line item:
    #
    #   - `id`              — line_items[0].product.id (Shopify product GID).
    #   - `url`             — line_items[0].product.online_store_url (or
    #                         derived from handle when null).
    #   - `year`, `season`, `sport`, `day`, `division` — parsed from the
    #     product's title/handle pattern (e.g.
    #     "Winter 2025 Thursday Open Volleyball" → year=2025, season="Winter",
    #     day="Thursday", division="Open", sport="Volleyball"). Sub-agent
    #     implements a small parser in `backend/utils/orders.py` (Stage 2
    #     Commit 2.3) — `parse_product_title(...)`. Falls back to product
    #     attributes (`product.product_type`, `product.tags`) when the title
    #     pattern fails.
    #   - `week1Start..week5Start` — derived from `SeasonDates.from_html`
    #     parsing of `line_items[0].product.description_html`. Each is the
    #     ISO date of that week's session; absent or unparseable weeks
    #     resolve to `None`.

    def _build_product_info(self, order: Box, season: SeasonDates) -> ProductInfo:
        ...  # see field-extraction strategy above

    def _build_order_info(self, order: Box, total_paid: Decimal) -> OrderInfo:
        ...

    def _resolve_season(self, order: Box, *, override=None) -> SeasonDates:
        """Pick the season dates for `order`, preferring an explicit override
        when given. Falls back to parsing the product-description HTML (which
        is what `refund_calculator.SeasonDates.from_html` already does).

        Returns an all-`None` `SeasonDates` when the season cannot be derived;
        `_apply_tier` then routes to the "season-missing" branch via
        `RefundResult.error()`.
        """
        if override is not None:
            from datetime import datetime as _dt
            return SeasonDates(start_date=f"{override.month}/{override.day}/{override.year}")
        line_items = order.get("line_items") or []
        product_html = (
            line_items[0].product.description_html
            if line_items and line_items[0].product is not None
            else None
        )
        if not product_html:
            return SeasonDates()
        return SeasonDates.from_html(product_html)

    def _apply_tier(
        self,
        season: SeasonDates,
        total_paid: Decimal,
        refund_to: str,
        submitted_at: datetime,
    ) -> TierEstimate:
        """Run one ladder. Translates `RefundResult` into the wire-shape
        `TierEstimate` (a TypedDict — NOT Pydantic; D28).

        Tier ladder logic (mirrors `refund_calculator.py`):

          # Pseudocode — see refund_calculator.estimate_refund_due (canonical)
          IF total_paid == 0:
              RETURN RefundResult.no_payment_made()           # notes: "no payment"
          IF NOT season.start_date OR total_paid < 0:
              RETURN RefundResult.error()                      # notes: "season unparseable"
          schedule = season.to_schedule()                      # WeekSchedule
          tiers    = REFUND_TIERS if refund_to == "original_method" else CREDIT_TIERS
          (tier, idx) = schedule.resolve_tier(submitted_at, tiers, season.is_short)
          IF tier IS None:
              RETURN RefundResult.zero(timing="after week 5")  # past all cutoffs
          RETURN RefundResult(
              amount      = (tier.percentage / 100) * total_paid,
              percentage  = tier.percentage,
              penalty     = tier.penalty,
              timing      = timing_label(idx),
              has_processing_fee = (refund_to == "original_method")
          )
        """
        kind = (
            EstimateTierKind.REFUND_TO_ORIGINAL
            if refund_to == "original_method"
            else EstimateTierKind.STORE_CREDIT
        )
        result: RefundResult = estimate_refund_due(season, float(total_paid), kind, submitted_at=submitted_at)
        return {
            "amount": float(result.amount),
            "percentage": result.percentage,
            "tierLabel": result.timing or "",
            "appliedProcessingFee": 0.05 if result.has_processing_fee else 0.0,
            "notes": ([] if result.success else ["estimate_error"]) + (
                ["no_payment_made"] if result.no_payment else []
            ),
        }

    @staticmethod
    def _extract_total_paid(order: Box) -> Decimal:
        if order.total_price_set and order.total_price_set.shop_money:
            return Decimal(str(order.total_price_set.shop_money.amount))
        return Decimal("0")
```

### 2.d — Utility extraction (concrete file moves)

Each util gets a single import-rewrite per call site; signatures are unchanged.

| Util                             | Source (file:lines)                                                                  | Target (file)             | Function name               | Signature change?                              |
| -------------------------------- | ------------------------------------------------------------------------------------ | ------------------------- | --------------------------- | ---------------------------------------------- |
| `parse_season_start_date(s)`     | `backend/legacy/shared/date_utils.py:170-205` (approx — sub-agent confirms via grep) | `backend/utils/dates.py`  | `parse_season_start_date`   | None — same `(str) -> date \| None` signature. |
| `parse_off_dates(s)`             | `backend/legacy/shared/date_utils.py` (same file, sibling helper)                    | `backend/utils/dates.py`  | `parse_off_dates`           | None.                                          |
| `weeks_into_season(now, …)`      | `backend/legacy/shared/date_utils.py` (look for `def weeks_into_season`)             | `backend/utils/dates.py`  | `weeks_into_season`         | None.                                          |
| `Money` / `format_money`         | scattered (see grep below)                                                           | `backend/utils/money.py`  | `format_money`, `Money`     | None.                                          |
| `to_decimal(s)` (defensive cast) | scattered                                                                            | `backend/utils/money.py`  | `to_decimal`                | None.                                          |
| `strip_order_number_prefix(s)`   | scattered (`#48957` → `48957`)                                                       | `backend/utils/orders.py` | `strip_order_number_prefix` | None.                                          |

> Sub-agent runs `grep -rn "def parse_season_start_date\|def parse_off_dates\|def weeks_into_season\|def format_money\|def to_decimal\|def strip_order_number_prefix" backend/ --include='*.py'`
> to confirm exact source line numbers before moving. The line numbers above
> are approximate — only the file paths are authoritative.

**Three commits, one PR each:**

- **Commit 2.1 — date utilities.** Create `backend/utils/dates.py` with the
  three date helpers; rewrite all `from legacy.shared.date_utils import …`
  imports of these symbols; ship `backend/modules/refunds/tests/test_refund_dates.py`
  covering the three helpers via fixture-driven cases lifted from
  `backend/legacy/shared/tests/test_date_utils_weeks.py`. **Do not** delete
  `legacy/shared/date_utils.py` yet — other unrelated helpers may still live there.
- **Commit 2.2 — money utilities.** Create `backend/utils/money.py` with
  `Money`, `format_money`, `to_decimal`. Rewrite all callers.
- **Commit 2.3 — order utilities.** Create `backend/utils/orders.py` with
  `strip_order_number_prefix`. Rewrite all callers.

### 2.e — Controller wiring (`backend/routes.py:84` stub replacement)

```python
# backend/modules/refunds/controllers/refunds_controller.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from modules.refunds.models.refund_request import RefundRequest
from modules.refunds.services.estimate_service import EstimateService

router = APIRouter(prefix="/refunds", tags=["refunds"])


def get_estimate_service() -> EstimateService:
    # Plain factory — DI lives at the FastAPI layer; tests pass overrides.
    return EstimateService()


# `response_model` is `dict` (or omitted entirely) — D28: outgoing responses
# constructed by the backend are NOT Pydantic models. The service returns a
# fully-built `RefundRequestEval` dict and the controller passes it through.
@router.post("/validate")
async def validate_refund(
    body: RefundRequest,
    service: EstimateService = Depends(get_estimate_service),
) -> dict:
    submitted_at = datetime.now(timezone.utc)
    return await service.compute_estimate(
        body.to_estimate_request(submitted_at=submitted_at),
    )
```

**Route mounting.** `backend/routes.py:84` currently declares
`async def validate_refund_request()` returning `Response(status_code=204)`
(verified — the entire `refunds = APIRouter(prefix="/refunds")` block lives at
lines 86-115 and is mounted via `router.include_router(refunds)` at line 153).
Stage 2 replaces the stub by:

1. Removing the inline stub functions for `/refunds/validate`, `/refunds/create`,
   `/refunds/update`, `/refunds/approve`, `/refunds/deny`, `/refunds/{refund_id}`
   from `backend/routes.py` (Stage 2 owns `validate`; Stages 5 own the others).
2. Adding `from modules.refunds.controllers.refunds_controller import router as refunds_router`
   at the top of `backend/routes.py`.
3. Replacing `router.include_router(refunds)` (line 153) with
   `router.include_router(refunds_router)`.

Stages 5/6 expand the controller with `/refunds/create` etc. — the Stage 2
sub-agent leaves placeholders (`@router.post("/")` returning 204) for those
routes inside `refunds_controller.py` so the router shape is stable.

### 2.f — Test parity strategy (deferred)

Parity tests are deferred to a later stage. Planned file:
`backend/modules/refunds/tests/test_estimate_service.py` — will fixture-port
the legacy refund-calculator suite cases verbatim and assert numerical
equivalence. No tests are built as part of Stage 2.

### 2.g — Stage 2 deliverables

- [ ] `backend/modules/refunds/services/estimate_service.py` —
      `EstimateService.compute_estimate` returns a `RefundRequestEval` dict.
- [ ] `backend/modules/refunds/models/estimate.py` — `EstimateRequest`
      (internal value object), `TierEstimate` / `OrderInfo` / `ProductInfo` /
      `EstimateBlock` / `RefundRequestEval` (TypedDicts — NOT Pydantic; D28).
- [ ] `backend/modules/refunds/models/refund_request.py` — Pydantic
      `RefundRequest` (incoming validate body): required `requesterEmail`,
      `requesterFirstName`, `requesterLastName`; optional `notes`,
      `transferRequest`, `sheetRowRef`, `isTest` (default False). NO `source`,
      `slackChannel`, or `policyConfirmation` fields.
- [ ] `backend/modules/refunds/controllers/refunds_controller.py` —
      `POST /refunds/validate` controller; `response_model=dict` (or omitted).
- [ ] `backend/utils/dates.py`, `backend/utils/money.py`, `backend/utils/orders.py`
      — extracted utilities (3 commits per § 2.d).
- [ ] `backend/routes.py` — refunds router included; the inline `/refunds/*`
      stubs (lines 84-115 currently) replaced by
      `router.include_router(refunds_router)`. Existing endpoints
      (`/products`, `/orders`, `/waitlists`) stay untouched.
- [ ] Three legacy duplicate calculators deleted per the inventory table
      (`modules/refunds/calculate_refund_due.py`,
      `modules/refunds/app/calculate_refund_due.py`,
      `modules/orders/services/orders_service_old.py`).
- [ ] **Gating dependency:** `backend/legacy/registrations/services/refunds_service.py`
      has its imports rewritten from
      `from utils.refund_calculator import (EstimateTierKind, RefundResult, SeasonDates, estimate_refund_due)`
      (line 11) to
      `from modules.refunds.refund_calculator import (EstimateTierKind, RefundResult, SeasonDates, estimate_refund_due)`
      **BEFORE** the legacy duplicate at
      `backend/legacy/registrations/utils/refund_calculator.py` is deleted.
      The Stage 2 sub-agent enforces this ordering (call out in the PR
      description; the migration commit and the delete commit are separate).
- [ ] `backend/tests/modules/refunds/test_refund_calculator.py` continues to
      pass unchanged (no regression in the pure tier-math layer).

#### Tests planned (deferred — file names only)

All tests are deferred to a later stage. Build these in a later stage:

- `backend/modules/refunds/tests/test_estimate_service.py` (parity port —
  see § 2.f)
- `backend/modules/refunds/tests/test_estimate_controller.py`
- `backend/modules/refunds/tests/test_refund_dates.py` (date utilities — § 2.d Commit 2.1)

---

## Stage 3 — Backend → Shopify request consolidation [DETAILED]

> Goal: every backend cancel + refund Shopify call flows through one
> service-layer wrapper, `ShopifyRefundService`, that calls the canonical
> `schema`-registry client at
> `backend/lib/clients/shopify-client/shop_client.py`. Existing
> direct-`schema.run` callers are migrated to the wrapper. The older
> `backend/lib/clients/shopify_client/client.py` (deprecated) is left alone.

### 3.a — Confirm the canonical GQL client path

Two Shopify clients exist in the repo:

| Path                                                | Style                                                                                                                    | Used by live cancel/refund?                                                                                                                                                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/lib/clients/shopify-client/shop_client.py` | Typed schema registry (`gql`/`gql.dsl`); `ShopifyClient.run(op, **kwargs)` over `Var`/`QueryOp`/`MutationOp`/`Resource`. | **Yes.** `backend/legacy/services/refunds/service.py` (lines 187, 225, 238) and `backend/legacy/services/orders/service.py:45` already call its `schema.orders.mutations.cancel` / `schema.refunds.mutations.create`. |
| `backend/lib/clients/shopify_client/client.py`      | Older `ShopifyClient.send_request(...)` style, no schema registry.                                                       | **No** in the live cancel/refund path.                                                                                                                                                                                |

**Decision (D10): anchor on `backend/lib/clients/shopify-client/shop_client.py`**
as the canonical client. Verified by:

```bash
grep -rn "schema.refunds.mutations.create\|schema.orders.mutations.cancel" backend/ \
  --include='*.py' --exclude-dir=__pycache__ --exclude-dir=.venv
```

…which returns matches only in `backend/legacy/services/refunds/service.py`,
`backend/legacy/services/orders/service.py`, and the canonical client itself.
The schema registry already exposes everything Stage 5 needs:

- `schema.orders.queries.by_id(id=...)` — full-detail order fetch (line items,
  transactions, refunds, custom_attributes, customer).
- `schema.orders.queries.by_name(name="#48957")` — order lookup by Shopify
  display name.
- `schema.orders.mutations.cancel(order_id, reason, restock, notify_customer, staff_note, refund_method)`
  — already wired to `orderCancel`. The mutation does NOT take a `refund` flag
  (Shopify GraphQL doesn't expose one on `orderCancel`); cancellation is pure
  cancel by default. Pass `refund_method=None` to preserve the
  cancel-without-implicit-refund invariant.
- `schema.refunds.mutations.create(order_id, currency, note, notify, transactions, refund_methods, refund_line_items, shipping)`
  — already wired to `refundCreate` with `wrap_into="input"` and
  `idempotent=True`.

The older `backend/lib/clients/shopify_client/client.py` is **deprecated**.
Stage 3 does NOT delete it (other modules — `analyze_refunds.py` plus various
non-refund scripts — still import it), but no new code in this spec calls it.

### 3.b — `ShopifyRefundService` — the new service wrapper

No new mutation descriptors needed. Stage 3 adds a thin service wrapper that
all backend cancel/refund call sites use:

```python
# backend/modules/refunds/services/shopify_refund_service.py
from decimal import Decimal
from typing import Literal, Optional

from box import Box
# Canonical schema-registry client (D10 anchor).
from lib.clients.shopify_client.shop_client import ShopifyClient, schema
# ↑ Note: import path uses the canonical hyphenless package name. The
#   filesystem directory is `backend/lib/clients/shopify-client/` (with a
#   hyphen) — Stage 3 does NOT rename the directory; instead it relies on
#   `uv.sources` / `pyproject.toml` `[tool.uv.sources]` mapping (already in
#   place — verified by `backend/pyproject.toml`). If the import fails, the
#   sub-agent investigates the existing import-path mechanism in
#   `backend/legacy/services/refunds/service.py:13` (which uses
#   `from shopify_client.shop_client import ShopifyClient, schema`) and
#   replicates whatever path mechanism is in use.

ShopifyOrder = Box  # alias for clarity


class ShopifyUserError(Exception):
    """Raised when Shopify returns non-empty user_errors on a mutation. The
    FastAPI exception middleware maps this to a 422 response."""

    def __init__(self, mutation: str, errors: list[dict]) -> None:
        super().__init__(f"{mutation}: {errors}")
        self.mutation = mutation
        self.errors = errors


class ShopifyRefundService:
    """Single backend entry point for Shopify cancel + refund mutations.

    Every backend module that needs to cancel an order or create a refund
    calls one of the three public methods below. Direct
    `client.run(schema.orders.mutations.cancel, ...)` calls outside this
    service are forbidden (verified by grep — see 3.f).
    """

    def __init__(self, client: Optional[ShopifyClient] = None) -> None:
        self._client = client

    @property
    def client(self) -> ShopifyClient:
        if self._client is None:
            import os
            self._client = ShopifyClient(
                store_id=os.environ["SHOPIFY__STORE_ID"],
                api_version=os.environ["SHOPIFY__API_VERSION"],
                token=os.environ["SHOPIFY__TOKEN__ADMIN"],
            )
        return self._client

    async def fetch_order_for_refund(
        self,
        *,
        order_id: Optional[str] = None,
        order_number: Optional[str] = None,
    ) -> Optional[ShopifyOrder]:
        """Fetch a single order with refund-grade detail (line items,
        custom_attributes, customer, refunds, transactions).

        Preconditions:
          - Exactly one of `order_id` or `order_number` is non-None.
          - When `order_number` is provided, may include or omit the leading "#".

        Postconditions:
          - Returns a Box-wrapped order dict with snake_case keys, or None
            when no order matches `order_number` (id-based lookups raise).

        Raises:
          - `ValueError` when both id and number are missing.
          - The underlying gql/httpx exceptions on transport failure.
        """
        if not order_id and not order_number:
            raise ValueError("fetch_order_for_refund requires order_id or order_number")
        if order_id is None:
            name = order_number if order_number.startswith("#") else f"#{order_number}"
            matches = self.client.run(schema.orders.queries.by_name, name=name)
            if not matches:
                return None
            order_id = matches[0].id
        return self.client.run(schema.orders.queries.by_id, id=order_id)

    async def cancel_order(
        self,
        *,
        order_id: str,
        approved_by: str,
        reason: str = "CUSTOMER",
        restock: bool = False,
        notify_customer: bool = False,
    ) -> dict:
        """Cancel a Shopify order without issuing an implicit refund.

        Preconditions:
          - `order_id` is a Shopify order GID or numeric digits string;
            `ShopifyClient` GID-coerces either form.
          - `reason` is a valid `OrderCancelReason` enum value (CUSTOMER,
            DECLINED, FRAUD, INVENTORY, OTHER, STAFF).

        Postconditions:
          - Returns Shopify's `OrderCancelPayload` dict with `job.id` /
            `job.done` fields (the cancel runs as a Shopify job).
          - The mutation does NOT include `refund_method`, so cancel never
            implicitly refunds (Property 7).

        Raises:
          - `ShopifyUserError` when the response contains non-empty
            `orderCancelUserErrors`.
        """
        payload = self.client.run(
            schema.orders.mutations.cancel,
            order_id=order_id,
            reason=reason,
            restock=restock,
            notify_customer=notify_customer,
            staff_note=f"Slack-approved cancel (by {approved_by})",
        )
        if payload.user_errors:
            raise ShopifyUserError("orderCancel", list(payload.user_errors))
        return payload.to_dict()

    async def create_refund(
        self,
        *,
        order_id: str,
        amount: Decimal,
        refund_to: Literal["original_method", "store_credit"],
        currency: str = "USD",
        notify: bool = False,
        note: Optional[str] = None,
        transactions: Optional[list[dict]] = None,
    ) -> dict:
        """Issue a Shopify refund. Routes to the original-payment branch or
        the store-credit branch based on `refund_to`.

        Preconditions:
          - `order_id` is a Shopify order GID or numeric digits string.
          - `amount > 0`. (Zero-amount refunds short-circuit at the caller.)
          - When `refund_to == "original_method"` and `transactions` is None,
            this method internally re-fetches the order and calls
            `_build_refund_transactions_for_shopify(order_id, amount, txns)`
            to derive the correct `[OrderTransactionInput!]` from the order's
            successful SALE/CAPTURE transaction.

        Postconditions:
          - Returns Shopify's `RefundCreatePayload` dict with `refund.id`,
            `refund.note`, `refund.created_at`, `refund.total_refunded_set.*`,
            `order.id`, `order.name`.

        Raises:
          - `ShopifyUserError` when `userErrors` is non-empty (e.g. duplicate
            refund attempt → Shopify's own dedup rejects → mapped to 422 via
            the FastAPI middleware).
          - `ShopifyUserError("refundCreate", [{"message": "No successful SALE/CAPTURE …"}])`
            when the order has no eligible parent transaction (re-raised
            from `_build_refund_transactions_for_shopify`).
        """
        note = note or "Refund approved via Slack workflow"
        if refund_to == "store_credit":
            refund_methods = self._build_store_credit_refund_methods(amount, currency)
            payload = self.client.run(
                schema.refunds.mutations.create,
                order_id=order_id,
                currency=currency,
                note=note,
                notify=notify,
                refund_methods=refund_methods,
            )
        else:  # original_method
            if transactions is None:
                order = await self.fetch_order_for_refund(order_id=order_id)
                transactions = list(order.transactions or []) if order else []
            txns = self._build_refund_transactions_for_shopify(order_id, amount, transactions)
            payload = self.client.run(
                schema.refunds.mutations.create,
                order_id=order_id,
                currency=currency,
                note=note,
                notify=notify,
                transactions=txns,
            )
        if payload.user_errors:
            raise ShopifyUserError("refundCreate", list(payload.user_errors))
        return payload.to_dict()

    # ── Parent-transaction helpers (moved from legacy/services/refunds/service.py) ──

    @staticmethod
    def _parent_capture_txn(transactions: list[dict]) -> Optional[dict]: ...

    @staticmethod
    def _build_refund_transactions_for_shopify(
        order_id: str, amount: Decimal, transactions: list[dict],
    ) -> list[dict]: ...

    @staticmethod
    def _build_store_credit_refund_methods(amount: Decimal, currency: str) -> list[dict]: ...
```

### 3.c — Inventory of call sites to migrate

```bash
grep -rn "schema.orders.mutations.cancel\|schema.refunds.mutations.create" backend/ \
  --include='*.py' --exclude-dir=__pycache__ --exclude-dir=.venv
```

| File:line                                              | Current call                                                                                                                                             | Migration                                                                                                                                                                |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `backend/legacy/services/refunds/service.py:187`       | `client.run(schema.orders.mutations.cancel, order_id=..., reason="CUSTOMER", restock=False, notify_customer=False, staff_note=..., idempotency_key=...)` | Replace with `await ShopifyRefundService().cancel_order(order_id=..., approved_by=...)`.                                                                                 |
| `backend/legacy/services/refunds/service.py:225`       | `client.run(schema.refunds.mutations.create, idempotency_key=..., **create_body.model_dump(...))` (the `execute_refund_create` orchestrator)             | Replace with `await ShopifyRefundService().create_refund(order_id=..., amount=..., refund_to=..., notify=..., transactions=...)`.                                        |
| `backend/legacy/services/refunds/service.py:238`       | `client.run(schema.refunds.mutations.create, **body.model_dump(...))` (low-level `create()` helper)                                                      | **Delete** the function — `ShopifyRefundService.create_refund` supersedes it. Verify no other consumer first.                                                            |
| `backend/legacy/services/orders/service.py:45`         | `client.run(schema.orders.mutations.cancel, order_id=order_id, reason=body.reason, ...)`                                                                 | Replace with `await ShopifyRefundService().cancel_order(order_id=..., approved_by=..., reason=body.reason, restock=body.restock, notify_customer=body.notify_customer)`. |
| `aws/lambda/functions/ShopifyRefundHandler/handler.py` | (Lambda — out of scope for Stage 3.)                                                                                                                     | **Out of scope.** Stage 5 supplants the Lambda path; Stage 3 only consolidates the FastAPI side. The Lambda is read-only for Stage 5's port of the store-credit branch.  |

**Verification command** (run after migration):

```bash
grep -rn "schema.refunds.mutations.create\|schema.orders.mutations.cancel" backend/ \
  --include='*.py' --exclude-dir=__pycache__ --exclude-dir=.venv \
  | grep -v "shopify_refund_service.py" \
  | grep -v "lib/clients/shopify-client/shop_client.py"
```

Expected output: zero lines (the only remaining matches are inside the
service wrapper itself and the canonical client's docstring/main guard).

### 3.d — Parent-transaction helper logic (move + adapt)

Existing helpers in `backend/legacy/services/refunds/service.py`:

| Helper                                                                   | Lines            | Move to                                                                         | Notes                                                                                                                                                                                                                 |
| ------------------------------------------------------------------------ | ---------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_parent_capture_txn(transactions)`                                      | 145-151 (approx) | `ShopifyRefundService._parent_capture_txn` (`@staticmethod`)                    | Unchanged logic: return the first txn whose `(kind, status)` matches `("CAPTURE"\|"SALE", "SUCCESS")`.                                                                                                                |
| `_build_refund_transactions_for_shopify(order_id, amount, transactions)` | 154-173 (approx) | `ShopifyRefundService._build_refund_transactions_for_shopify` (`@staticmethod`) | Unchanged logic. Raises `ShopifyUserError("refundCreate", [{"message": "No successful SALE/CAPTURE …"}])` when no parent is found (currently raises `UnprocessableError`; rebrand to the service's domain exception). |
| `_build_store_credit_refund_methods(amount, currency)`                   | 176-180 (approx) | `ShopifyRefundService._build_store_credit_refund_methods` (`@staticmethod`)     | Unchanged logic. Returns `[{"storeCreditRefund": {"amount": {"amount": "<2dp>", "currencyCode": currency}}}]`.                                                                                                        |

> Sub-agent confirms exact line numbers via
> `grep -n "_parent_capture_txn\|_build_refund_transactions_for_shopify\|_build_store_credit_refund_methods" backend/legacy/services/refunds/service.py`
> before the move. The line numbers above are approximate (verified
> manually as 145-180 range during the design pass).

After the move, `backend/legacy/services/refunds/service.py` either delegates
to the new service for the cancel + refund branches OR retains its existing
`async def execute_refund_create(...)` orchestrator (which Stage 5 supplants
on the FastAPI side). Stage 3 prefers **delegation** — replace the bodies of
`execute_refund_create` / `cancel` etc. with calls to `ShopifyRefundService`
methods, leaving the legacy module's external API stable until Stage 5
removes it entirely.

### 3.e — Error handling

| Failure mode                                | Where caught                                                                                                                                                                     | HTTP response                                                                                                     |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Shopify `userErrors` non-empty              | `ShopifyRefundService` raises `ShopifyUserError`                                                                                                                                 | FastAPI middleware (`backend/core/api_errors.py`) maps `ShopifyUserError` → **422** with the user-error messages. |
| Network failure (`httpx` exception)         | Bubbles up from `ShopifyClient.run`                                                                                                                                              | FastAPI middleware → **502 Bad Gateway** with a redacted error message; full trace logged.                        |
| Missing parent SALE/CAPTURE                 | `_build_refund_transactions_for_shopify` raises `ShopifyUserError("refundCreate", [{"message": "No successful SALE/CAPTURE transaction found for refund to original payment"}])` | Same as the generic `ShopifyUserError` mapping → **422** with the explanatory message.                            |
| `fetch_order_for_refund` returns `None`     | Caller (e.g. `EstimateService`)                                                                                                                                                  | Caller raises a domain exception (`OrderNotFoundError`); FastAPI middleware maps to **404**.                      |
| Validation error on inputs (bad enum, etc.) | FastAPI's Pydantic validation                                                                                                                                                    | **422** with the standard FastAPI Pydantic-error payload.                                                         |

`ShopifyUserError` is registered with FastAPI in `backend/main.py` next to the
existing `handle_unhandled_exception` handler. The Stage 3 sub-agent adds the
`@app.exception_handler(ShopifyUserError)` decoration alongside the import.

### 3.f — Stage 3 deliverables

- [ ] `backend/modules/refunds/services/shopify_refund_service.py` exists
      and exposes `fetch_order_for_refund`, `cancel_order`, `create_refund`
      with the docstrings above.
- [ ] Every backend cancel/refund call site has been rewritten to call
      `ShopifyRefundService`. **Verified by:**
      `grep -rn "schema.refunds.mutations.create\|schema.orders.mutations.cancel" backend/ --include='*.py' --exclude-dir=__pycache__ --exclude-dir=.venv | grep -v shopify_refund_service.py | grep -v "lib/clients/shopify-client/shop_client.py"`
      returns zero lines.
- [ ] Parent-transaction helpers (`_parent_capture_txn`,
      `_build_refund_transactions_for_shopify`,
      `_build_store_credit_refund_methods`) moved from
      `backend/legacy/services/refunds/service.py` to
      `ShopifyRefundService` as static methods. Helpers are
      **business-agnostic** — they take primitive inputs (transactions list,
      amount as `Decimal`, currency code as `str`) and return primitive
      outputs (`[OrderTransactionInput!]`-shaped list of dicts). They take
      no `RefundRequest` / domain objects directly. (D31.)
- [ ] All `ShopifyRefundService` method bodies use the existing canonical
      pattern verbatim: `self.client.run(schema.<resource>.<queries|mutations>.<name>, **kwargs)`
      — verified against `backend/lib/clients/shopify-client/shop_client.py`
      and existing successful call sites in
      `backend/legacy/services/refunds/service.py:187,225,238` and
      `backend/legacy/services/orders/service.py:45`. NO constructor-based
      mutation invocations (e.g. no `OrderCancelMutation(input=...)`), NO
      typed input dataclasses, NO `MutationOp(...)` direct construction in
      calling code. (D31.)
- [ ] `backend/lib/clients/shopify_client/` (with the underscore — the
      deprecated dir) is NOT referenced for any client-instrumentation
      logic. (D31.)
- [ ] `ShopifyUserError` exception class lives in
      `shopify_refund_service.py`; `backend/main.py` registers an
      `@app.exception_handler(ShopifyUserError)` mapping to 422.
- [ ] `backend/lib/clients/shopify_client/client.py` is **left untouched**.
      No deprecation pass, no rename, no migration of pre-existing callers
      (out of scope for this spec; documented as deprecated in D10).

#### Tests planned (deferred — file names only)

All tests are deferred to a later stage. Build these in a later stage:

- `backend/modules/refunds/tests/test_shopify_refund_service.py`

### 3.g — Decision log addition

Already added as **Decision D10** in the Decisions Log: anchor on
`backend/lib/clients/shopify-client/shop_client.py`. The older
`backend/lib/clients/shopify_client/client.py` is documented as deprecated;
no new code uses it; no migration of existing non-refund callers is required
for this spec.

### 3.h — Name-conflict check

| New symbol                                    | Existing symbol(s)                                                      | Conflict?                                                                                                                          |
| --------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `ShopifyRefundService` (class)                | none                                                                    | None.                                                                                                                              |
| `ShopifyUserError` (exception)                | none in `backend/`                                                      | None — sibling to existing `UnprocessableError` in `backend/legacy/services/refunds/service.py`; NOT a rename of the legacy class. |
| `ShopifyRefundService.cancel_order`           | `cancel(order_id, body)` in `backend/legacy/services/orders/service.py` | None — different module + different method name; legacy stays in place during migration.                                           |
| `ShopifyRefundService.create_refund`          | `create(body)` in `backend/legacy/services/refunds/service.py`          | None — different module + different method name.                                                                                   |
| `ShopifyRefundService.fetch_order_for_refund` | `fetch_order(req)` in `backend/legacy/services/refunds/service.py`      | None — different module; the new method takes kwargs vs the legacy positional arg.                                                 |

---

## Stage 4 — Validation response shape (Slack-ready blocks) [SKELETON]

See [design-stage-4.md](./design-stage-4.md).

---

## Stage 5 — Cancel + refund execution [SKELETON]

See [design-stage-5.md](./design-stage-5.md).

---

## Stage 6 — Final response shape [SKELETON]

See [design-stage-6.md](./design-stage-6.md).

---

## Stage 7 — Slack final message [SKELETON]

See [design-stage-7.md](./design-stage-7.md).

---

## Correctness Properties

These are example-based invariants the implementation must hold. They are
documentation of invariants the implementation must hold — the verification
mechanism (tests, grep checks) is deferred. No PBT (D8).

### Property 1: Unprocessed-only filter (Stage 1)

For any sheet snapshot, the picker modal lists only rows for which the
inlined check `!!row.statusCellValue?.trim()` is `false`. Adding a row to
the sheet with the `Status` cell empty (or whitespace-only) makes it appear;
setting `Status` to any non-empty value hides it on the next fetch. There is
no fallback to color/highlight detection. The check is inlined at every call
site — there is no `isProcessedRow` helper (D26) — but the behavioral spec is
unchanged: a row is unprocessed iff `statusCellValue` is null/empty/whitespace;
setting it to anything non-empty hides the row on the next fetch.

### Property 2: Modal reuse, no field duplication (Stage 1)

The approval modal opened from the sheet flow uses the _same_
`BuildApproveModalArgs` shape as the webhook flow. Any field added to the
modal must come from `validateRefund`'s response, not from a new struct in
`domain/refund/`.

### Property 3: Channel routing (Stage 1)

The review card's destination channel is the result of
`slackChannel ?? Deno.env.get("SLACK_CHANNEL__REFUNDS__DEFAULT") ?? "#joe-test"`,
evaluated in the Slack handler. Per-request `slackChannel` (operator-supplied
via the picker) wins; in its absence the env-var default applies; in its
absence the hardcoded `"#joe-test"` applies. There is no fourth path. The
existing `REFUND_TEST_CHANNEL` and `REFUND_REVIEW_CHANNEL` env vars are not
read by the new flow.

### Property 4: Estimate consolidation parity (Stage 2)

For every test case in
`backend/tests/modules/refunds/test_refund_calculator.py`, the new
`EstimateService.compute_estimate(...)` returns numerically identical estimate
values (within `Decimal("0.01")` epsilon) when given an `EstimateRequest`
whose order's product-description-derived season and total reproduce the
test fixture's inputs.

### Property 5: No raw GraphQL outside the GQL client (Stage 3)

A repo-level grep for `mutation\s*\{|query\s*\{` returns matches only inside
`backend/lib/clients/shopify-client/` (the canonical client) and
`backend/lib/clients/shopify_client/` (the deprecated OLD client; not
referenced by Stage 3). No matches in `backend/modules/`,
`backend/controllers/`, or elsewhere.

### Property 6: Backend never builds Block Kit (Stages 2, 5)

Every backend response from `/refunds/validate` and `/refunds/create` is a
plain dict / TypedDict whose fields are scalars, lists, and nested
TypedDicts — no `blocks: list[dict]` field, no Slack-SDK imports on the
backend, no Pydantic on the outgoing shape (D28).

### Property 7: Cancel without implicit refund (Stage 5)

For any `POST /refunds/create` with `cancel === true` and `refund === false`,
`schema.orders.mutations.cancel` is invoked **without** a `refund_method`
argument. (The GQL `orderCancel` doesn't take a `refund` boolean; refusing to
pass `refund_method` preserves the no-implicit-refund invariant.)

### Property 8: All backend Shopify cancel/refund calls go through `ShopifyRefundService` (Stage 3)

For any new code path under `backend/modules/`, `backend/controllers/`, or
`backend/legacy/services/` that issues a Shopify cancel or refund mutation,
the call goes through `ShopifyRefundService.cancel_order` or
`ShopifyRefundService.create_refund`.

## Error Handling

| Scenario                                                                    | Where         | Response                                                                                                                                                                                                                                                  | Recovery                                                                                   |
| --------------------------------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Sheet read fails (network, auth)                                            | Stage 1 entry | Picker modal opens with empty list + an `:warning:` context block. Logs `[refund_review] sheet read failed: …`                                                                                                                                            | Operator retries; nothing partially applied.                                               |
| Sheet has zero unprocessed rows                                             | Stage 1 entry | Picker modal opens with a "Nothing to review" empty state and a Close button.                                                                                                                                                                             | N/A — happy "no work" path.                                                                |
| `/refunds/validate` returns 4xx                                             | Stage 1 → 2   | Picker submit shows an error context block in the picker modal (`response_action: "errors"`); does **not** push the approval modal.                                                                                                                       | Operator fixes the row in the sheet (e.g. invalid order number) and retries.               |
| `/refunds/validate` returns 5xx or times out                                | Stage 1 → 2   | Same as above plus a `:rotating_light:` context with the error id.                                                                                                                                                                                        | Manual: operator retries; backend logs the trace.                                          |
| `orderCancel` user error                                                    | Stage 5       | Backend returns `{ok: false, errors: [...orderCancelUserErrors...]}`. Slack reads `response.errors[]` and renders the error context block locally.                                                                                                        | No retry — the cancel is a no-op (Shopify atomically rejects). Operator decides next step. |
| `refundCreate` user error                                                   | Stage 5       | Same pattern as above. If a successful `orderCancel` already happened in the same call (cancel+refund both true), the response includes both outcomes — `cancel` populated, `refund` null, `errors[]` non-empty — so the operator sees the partial state. | Manual: operator issues the refund directly in Shopify or retries with corrected amount.   |
| `BARS_API_URL` not set                                                      | Stage 1       | Slack falls back to existing Lambda path (`REFUND_PROCESS_URL`). Picker modal still works; validate response is constructed locally from a mock.                                                                                                          | Set the env var to enable backend path.                                                    |
| Slack interactivity expired (>3s response)                                  | Stage 1       | Slack shows the standard "Something went wrong" toast.                                                                                                                                                                                                    | Operator re-runs `/eval-refund-request`.                                                   |
| Operator cancels picker modal                                               | Stage 1       | Workflow completes cleanly via `completeWithEmpty(client, body)` (existing helper in `shared/slack/workflow.ts`).                                                                                                                                         | None needed.                                                                               |
| Duplicate `POST /refunds/create` (same order, same amount, same `refundTo`) | Stage 5       | Shopify rejects the second `refundCreate` mutation with a user-error response. Backend returns 422 with the user-error message; Slack surfaces it in the final card. **No backend-side dedup store** — Shopify owns the invariant.                        | Operator inspects the order in Shopify Admin to confirm whether the prior refund landed.   |

## Open Questions

1. **Q1 — Green-highlight vs. status-column for "unprocessed" detection. ✅ RESOLVED.**
   Status column is the only source of truth: a row is unprocessed iff its
   `Status` cell is empty/null/whitespace. No color/highlight detection,
   no fallback. The check is the inlined one-liner
   `!!cellValues[statusColumnIndex]?.trim()` at every call site — there is
   no `isProcessedRow` helper (D26).
   See Decision D3.

2. **Q2 — Slash command name + scope. ✅ RESOLVED.**
   Command name is `/eval-refund-request` (workspace-scope, since the existing
   app already declares `commands` in `botScopes`). See Decision D1 and the
   Stage 1 file inventory.

3. **Q3 — Refund sheet header names. ✅ RESOLVED.**
   Headers in the live `Refund_Requests` tab are listed inline in the
   "Column header resolution" subsection of Stage 1a. The parser resolves by
   case-insensitive substring search of the header text — header order is
   NOT trusted. The match algorithm is "for each logical field, try each
   candidate substring in order; first hit wins; on no match → field is
   `null` and a warning is logged." The "refund policy" column is NOT
   matched (it has no consumer); per user direction the loader simply
   ignores it.

4. **Q4 — `orderMetadata` round-trip vs. re-fetch on `/refunds/create`. ✅ RESOLVED.**
   Only `orderId` and `productId` round-trip via Slack `private_metadata`
   (~80 chars total of GIDs — well under the 3 KB ceiling). The backend
   re-fetches the order on `/refunds/create` to derive transactions,
   currency, and customer info fresh from Shopify. No opaque `orderMetadata`
   blob is round-tripped, and no Shopify re-fetch concern remains for the
   validate → create step (the re-fetch is intentional and cheap).

5. **Q5 — Idempotency-key store. ✅ RESOLVED (won't fix).**
   Shopify's own dedup on `refundCreate` (and the canonical `refund_create`
   mutation in `shop_client.py` is declared `idempotent=True`) errors on a
   duplicate refund attempt. Acceptable: the second `/refunds/create` POST
   returns 422 with the Shopify user-error message; the operator sees it in
   the final Slack card. No backend-side dedup store.

6. **Q6 — Store-credit refund path. ✅ RESOLVED.**
   Stage 5 ports the existing Lambda's store-credit branch verbatim into
   `ShopifyRefundService.create_refund` (Stage 3) — the store-credit branch
   inside that method calls `_build_store_credit_refund_methods` and passes
   `refund_methods=` to `schema.refunds.mutations.create`. Stage 5 wires
   `POST /refunds/create` directly through the controller and calls
   `ShopifyRefundService.cancel_order` and/or `ShopifyRefundService.create_refund`
   in sequence — there is NO `ExecuteService` orchestrator (D30). The Lambda
   lives at `aws/lambda/functions/ShopifyRefundHandler/handler.py`; the Stage 5
   sub-agent reads it for branch parity. The legacy refund-flow service
   (`backend/legacy/services/refunds/service.py`) already has scaffolding
   for the store-credit branch via `_build_store_credit_refund_methods`
   (lines ~174-180); the helper moves to `ShopifyRefundService` (Stage 3).

7. **Q7 — How is the `restockTo` lane consumed downstream? ✅ DEFERRED.**
   Shopify's `orderCancel` mutation only accepts a boolean `restock`
   flag; the richer per-lane semantics (`"veteran" | "early" | "general"
| "waitlist"`) need a separate consumer — likely an inventory-
   restock service that subscribes to a Shopify webhook (or that the
   controller calls in sequence after a successful cancel). Stage 5
   deliberately scopes that work out: it accepts the field, persists it
   on the wire (round-tripped through Slack), and maps it down to the
   boolean Shopify expects today (presence-of-`restockTo` → `restock=True`,
   per Stage 5 § 5.e). Status: deferred to inventory-restock follow-up
   spec; Stage 5 maps presence-of-`restockTo` → boolean and stops there.

---

## Decisions Log

| #   | Decision                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Why                                                                                                                                                                                                                                                                                                              |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- | ------------------------------------------------------------------------------------------------------------- |
| D1  | **Slash command** (not URL trigger) for Stage 1 entry.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | App already has `commands` scope; slash commands carry interactivity for free; matches the pattern of every other modal flow.                                                                                                                                                                                    |
| D2  | Default channel env var for the new `/eval-refund-request` flow: **`SLACK_CHANNEL__REFUNDS__DEFAULT`** (default `"#joe-test"`). Replaces all references to `REFUND_TEST_CHANNEL` and `REFUND_NOTIFICATION_CHANNEL` in the new flow. **Channel routing is fully resolved on the Slack side** — the backend's `/refunds/validate` request body does NOT accept any channel field. Precedence (highest first, applied inside `functions/send_request_for_eval.ts`): operator-supplied override on the picker modal's "post to channel" input → env-var `SLACK_CHANNEL__REFUNDS__DEFAULT` → hardcoded `"#joe-test"`. The Slack handler reads the resolved channel and uses it directly for `chat.postMessage` (no roundtrip through the backend). The existing `REFUND_TEST_CHANNEL` and `REFUND_REVIEW_CHANNEL` vars are NOT read by the new flow but are left untouched (the existing webhook-driven refund-evaluation flow keeps using them as-is).                                                                                        | Double-underscore convention matches the workspace's other `SLACK_CHANNEL__*` vars; the user wires the actual channel later via env, so the default falls through to `"#joe-test"`. The new var is read only by the new flow — touching the existing vars would risk breaking the existing webhook path.         |
| D3  | Default unprocessed-row detector: **Status column only**; empty/null/whitespace = unprocessed; no color/highlight detection.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | Status-column matches the existing waitlist pattern (`status_format.ts`, `status_write.ts`); highlight detection requires extra Sheets API calls + format parsing and adds ambiguity (RGB thresholds, conditional formatting, manual highlighting). Single rule, single source of truth.                         |
| D4  | **Reuse `views/refund/approve_modal.ts`** but as a **thin caller** of the new generic `views/_shared/approve_modal.ts` block builder (D23). All refund-specific labels, defaults, and action values are passed in by the caller; the generic builder has no refund domain knowledge. Net Stage 1 edit: the old file shrinks to a delegation layer plus the 1-line constant rename.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Maximum reuse, minimum duplication — but the reuse is now _parameterized_, not literal. The thin-caller pattern lets non-refund flows reuse the same approve-modal block layout without copy-pasting refund options.                                                                                             |
| D5  | **Pseudocode + TypeScript + Python** mixed (real syntax) — no abstract pseudocode.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | The codebase has fixed languages; abstract pseudocode would obscure detail the sub-agent needs.                                                                                                                                                                                                                  |
| D6  | Stages 1, 2, 3 run **in parallel**; Stage 1 mocks the backend until Stage 2 lands.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | Spelled out in Stage Map. The mock lives behind `validateRefund(client, body)` in `domain/refund/api.ts` (which calls the generic `clients/bars_api/client.ts`) — a few lines of JSON, no real HTTP.                                                                                                             |
| D7  | Backend exports use **new names** during Stage 2 (`estimate_refund_amount`) to avoid collisions with `estimate_refund_due` / `calculate_refund_due`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | User constraint: no name conflicts during transition.                                                                                                                                                                                                                                                            |
| D8  | **No PBT / property-based tests.** Example-based unit tests only.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | User preference.                                                                                                                                                                                                                                                                                                 |
| D9  | **No deny-path execution** in Stage 5. Existing Slack-side `handleDenyButton` stays as-is.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | User preference: approve-path-only.                                                                                                                                                                                                                                                                              |
| D10 | **Anchor on the canonical `gql.dsl` Shopify client at `backend/lib/clients/shopify-client/shop_client.py`** (rename to `shop_client/` in Stage 3 to make it a normal Python package). The schema-registry pattern (`schema.orders.queries.by_id`, `schema.orders.mutations.cancel`, `schema.refunds.mutations.create`) and the `Var`/`QueryOp`/`MutationOp`/`Resource` primitives are used verbatim — Stage 3 extends the existing registry, never invents a new descriptor pattern. The OLD client at `backend/lib/clients/shopify_client/` (underscore, non-`gql.dsl`) is fully deprecated with `@warnings.deprecated`; no wrappers, no compatibility shims.                                                                                                                                                                                                                                                                                                                                                                            | Verified by reading `shop_client.py`: `orderCancel` and `refundCreate` are already wired with full variable specs and idempotency. The OLD client predates `gql`/`gql.dsl` and is dead-end for new functionality.                                                                                                |
| D11 | **Two backend service classes for refunds:** `EstimateService` (Stage 2 — single estimate authority) and `ShopifyRefundService` (Stage 3 — single Shopify cancel/refund call site). NO orchestrator service: `POST /refunds/create` lives directly in the controller and calls `ShopifyRefundService.cancel_order(...)` and/or `ShopifyRefundService.create_refund(...)` in sequence based on the `cancel`/`refund` booleans on the request body. The if/else branching is ~10 lines and stays in the controller (D30). Each class lives in its own file under `backend/modules/refunds/services/`; controllers under `backend/modules/refunds/controllers/refunds_controller.py` are thin pass-throughs.                                                                                                                                                                                                                                                                                                                                 | User correction in this design pass — separate services keep responsibilities (estimate math vs. Shopify mutations) cleanly testable in isolation. Mirrors the way `OrdersService` already separates fetch/update/cancel concerns. The orchestrator service was deleted because the branching is trivial.        |     | Item 14 of design corrections. Simplifies the module layout and matches the existing FastAPI service pattern. |
| D12 | **Backend NEVER builds Slack Block Kit. AND outgoing responses are NOT Pydantic.** Backend responses are plain Python dicts / TypedDicts (`OrderInfo`, `ProductInfo`, `EstimateBlock`, etc.) constructed manually in the controller — Pydantic is reserved for incoming external request bodies (D28). The Slack app reads field paths directly into its own block builders. No `backend/modules/slack/block_builders/`, no `eval_payload_builder.py`, no `build_*_blocks` / `build_*_payload` functions, no `blocks: list[dict]` field anywhere.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Item 15 of design corrections. Inverts the prior design — Slack owns presentation, backend owns logic. D28 narrows the boundary further: Pydantic is for incoming validation only.                                                                                                                               |
| D13 | **Slash command name: `/eval-refund-request`.** Final naming alignment (D27): trigger = `start_refund_eval` in `triggers/start_refund_eval.ts`; workflow = `validate_refund_request` in `workflows/validate_refund_request.ts`; function = `send_request_for_eval` in `slack-apps/registrations/functions/send_request_for_eval.ts`. Refund approval modal callback id = `refund_approval_modal` (renamed from `approve_refund_modal`; the rename lives inside the thin caller `views/refund/approve_modal.ts`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | User correction — clarifies that the slash command + the layered identifiers (trigger/workflow/function) all reflect the "evaluate refund request" mental model, with each layer named after what it does at that layer.                                                                                         |
| D14 | **Channel env var `SLACK_CHANNEL__REFUNDS__DEFAULT`** (default `#joe-test`). Replaces references to `REFUND_TEST_CHANNEL` and `REFUND_NOTIFICATION_CHANNEL` in the new flow. **Channel routing happens entirely on the Slack side** — the backend's `/refunds/validate` request body does NOT include any channel field. Precedence (highest first, applied in `functions/send_request_for_eval.ts`): operator override on the picker modal's "post to channel" input → env-var → `#joe-test` literal.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | User correction — converges on a single canonical env var name with double-underscore separators per the workspace's other `SLACK_CHANNEL__*` vars.                                                                                                                                                              |
| D15 | **Status-column-only "unprocessed" detection.** A row is unprocessed iff its `Status` cell is empty/null/whitespace; the check is the inlined one-liner `!!row.statusCellValue?.trim()` at every call site (no `isProcessedRow` helper — D26 supersedes the earlier helper-based form). No green-highlight detection, no `effectiveFormat.backgroundColor` lookup, no `REFUND_SHEET_PROCESSED_DETECTOR` env var, no `sheet_format.ts` file.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | User correction — drops the cost + ambiguity of color detection in favor of a single-source-of-truth column predicate.                                                                                                                                                                                           |
| D16 | **Sheet column matching: case-insensitive substring with multiple candidate tokens per logical field.** Each logical field maps to an ordered list of substring tokens; the parser tries them in order and the first hit wins. Examples: `orderNumber` → `["order number"]`; `refundOrCredit` → `["store credit", "original form", "refund"]`; `transferRequest` → `["transfer to another day", "sport, day, and division"]`. Tokens are constants in `domain/refund/sheet_loader.ts` (D26). Header matching uses the generic `findColumn` helper in `shared/google/columns.ts`. Headers may appear in any order. The `RefundSheetEntry` type stores the **raw** cell value for `refundOrCredit`; normalization to `"original_method" \| "store_credit"` happens in `domain/refund/api.ts` (the typed call-site convenience layer). The "refund policy" column is **not** captured by the loader (the form gates submission on it; backend doesn't consume it; no consumer needs the cell value).                                         | User correction — sheet headers are long-form questions, not aliases; matching by exact alias would be brittle. The "refund policy" column is intentionally unread.                                                                                                                                              |
| D17 | **Round-trip metadata is two GIDs only:** `orderId` + `productId`. No opaque `orderMetadata` blob round-tripped through Slack `private_metadata`. The 3 KB ceiling concern is dropped. The backend re-fetches the order on `/refunds/create` to derive transactions, currency, and customer info fresh.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | User correction (item 8 / 9) — the round-trip is small (~80 chars of GIDs), so the dual-purpose `orderMetadata` design is unnecessary.                                                                                                                                                                           |
| D18 | **No idempotency-key store.** Shopify's own dedup on `refundCreate` (and the canonical `refund_create` mutation in `shop_client.py` is declared `idempotent=True`) errors on duplicate attempts. Backend does not maintain its own dedup mechanism. The `idempotencyKey` field on `/refunds/create` is dropped.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | User correction (item 10) — Shopify's GQL layer is the source of truth for refund dedup; a backend store would be redundant.                                                                                                                                                                                     |
| D19 | **Money helpers extracted to `backend/utils/money.py`** (Stage 2 Commit 2.2). `Money`, `format_money`, `to_decimal` move out of scattered call sites into a single utility module. The percentage-discount math stays inside `RefundEstimate` / `EstimateService` since it's tier-specific. Currency assumption: USD or store-credit only.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | User correction in this design pass — the utility-extraction scan (Stage 2 § 2.d) found ≥ 2 callers worth consolidating; supersedes the earlier "no money utils" stance.                                                                                                                                         |
| D20 | **Date utilities extracted to `backend/utils/dates.py`** (Stage 2 Commit 2.1). `parse_season_start_date`, `parse_off_dates`, `weeks_into_season` move out of `backend/legacy/shared/date_utils.py` into the canonical utility module. The internal `parse_date_mdy` / `parse_csv_dates` helpers in `backend/modules/refunds/refund_calculator.py` stay private to that module (already test-covered there). The deprecated `backend/utils/datetime/date_utils.py` re-exports stay untouched.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | User correction in this design pass — the legacy `date_utils.py` is being slowly emptied; these three helpers belong in `backend/utils/`. Supersedes the earlier "no new datetime utils" stance for these three helpers only.                                                                                    |
| D21 | **Order utilities extracted to `backend/utils/orders.py`** (Stage 2 Commit 2.3). `strip_order_number_prefix` (`#48957` → `48957`) moves to a single shared helper used by `EstimateService` and (Stage 5) the execute path.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Stage 2 Commit 2.3 — single shared helper avoids drift between validate and create flows.                                                                                                                                                                                                                        |
| D22 | **Generic BARS API client at `clients/bars_api/client.ts`.** Refund-agnostic single HTTP wrapper with `post<T>({endpoint, params?, body?, headers?})` and `get<T>({...})` methods, parameterized over response type. Default headers: `Content-Type`, `Accept`, and an optional `X-API-Key` sourced from env `BARS_API_KEY` (sent as `null` / omitted when unset; user wires real auth later). Base URL from `BARS_API_URL`. Refund-specific typed wrappers live in `domain/refund/api.ts` as pure call-site convenience (`validateRefund(client, body)`, `executeRefund(client, body)`); they contain no HTTP code.                                                                                                                                                                                                                                                                                                                                                                                                                      | User correction — the API client must be reusable across any backend route, not refund-specific. Same "generic, parameterized" principle as the picker / approve-modal builders.                                                                                                                                 |
| D23 | **Generic picker + approve modal block builders in `views/_shared/`.** Both modals are parameterized block builders with zero refund domain knowledge: `pickerModal({ items, formatItem, getItemId, callbackId, title, ... })` and `approveModal({ headerBlocks, actionOptions, amountInput, restockOptions, notifyToggle, callbackId, title, metadata })`. The refund flow uses `pickerModal` directly (the calling function provides refund-shaped items + a refund-specific `formatItem`); the approval modal has a thin caller at `views/refund/approve_modal.ts` that supplies refund config. The 1-line constant rename (`APPROVE_MODAL_CALLBACK_ID = "approve_refund_modal"` → `REFUND_APPROVAL_MODAL_CALLBACK_ID = "refund_approval_modal"`) lives in the thin caller.                                                                                                                                                                                                                                                            | User correction — same reusability principle as the BARS API client. The old `views/refund/pick_row_modal.ts` is deleted; the refund flow uses the generic `views/_shared/picker_modal.ts` directly. Sub-agent reads `shared/slack/list_modal.ts` first and decides whether to extend it or create a sibling.    |
| D24 | **Slack-side env var convention: `SHEET_ID__REFUND_REQUESTS` and `TAB_ID__REFUND_REQUESTS`.** Both are required at deploy (no defaults; fail fast if unset). Replaces the prior `REFUND_SHEET_ID` env var + the hardcoded `tab_id: 1435845892` default. Names follow the workspace's `__` separator convention (matches `SLACK_CHANNEL__REFUNDS__DEFAULT`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | User correction — converges on the workspace's double-underscore separator convention for both spreadsheet identifiers; eliminates a hardcoded tab id that would silently drift if the spreadsheet is ever rebuilt.                                                                                              |
| D25 | **Diagnostic fields dropped from `RefundSheetData`.** `totalRows`, `processedRows`, and `missingStatusColumn` are removed from the typed shape. `RefundSheetData` is now `{ url, spreadsheetId, tabId, unprocessed }`. The "missing Status column → all rows treated as unprocessed" graceful-degradation behavior still happens internally inside the loader; it just isn't surfaced as a typed flag.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | User correction — the diagnostic fields were never consumed by the modal; surfacing them on the wire shape was overkill. The graceful-degradation behavior is still there, just internal.                                                                                                                        |
| D26 | **`domain/refund/sheet.ts` split into `types.ts` (types only) + `sheet_loader.ts` (functions).** `findColumn` lifted to `shared/google/columns.ts` so it's reusable across any sheet (signature unchanged: `(headers: string[], substring: string) => number \| null`). Refund-specific column-token tables (`REFUND_OR_CREDIT_TOKENS`, etc.) stay in `sheet_loader.ts` and pass strings into the generic `findColumn`. `isProcessedRow` is **deleted**; the one-liner `!!row.statusCellValue?.trim()` is inlined at every call site.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | User correction — types-and-functions split lets type-only consumers import without pulling sheet-fetching code; lifting `findColumn` matches the same generic-helper principle as the BARS API client; deleting `isProcessedRow` removes a one-liner indirection that was never worth its own function name.    |
| D27 | **Naming alignment across layers** (supersedes intermediate naming in earlier passes): slash command `/eval-refund-request` → trigger `start_refund_eval` (file `triggers/start_refund_eval.ts`) → workflow `validate_refund_request` (file `workflows/validate_refund_request.ts`) → function `send_request_for_eval` (file `functions/send_request_for_eval.ts`). Each layer is named after what it does at that layer: the trigger _starts_ the eval, the workflow performs the _validation_, the function _sends a request_ to the backend for evaluation. Trigger display name is unchanged ("Evaluate Refund Request"); only file paths and callback ids change.                                                                                                                                                                                                                                                                                                                                                                    | User correction — cleanly differentiates the four conceptual layers (trigger / workflow / function / slash command) so prose, code samples, and file inventories all line up.                                                                                                                                    |
| D28 | **Pydantic is used only for external incoming request bodies.** Outgoing responses (constructed by the backend) and internal value objects use TypedDict / dataclass / dict — not Pydantic. `RefundRequestEval` is the canonical name for the validate-route response. The previous `ValidateRefundResponse` Pydantic shape is removed; the controller's `response_model` is `dict` (or omitted entirely). The validate response's wire fields are: `ok`, `isValid`, optional `validationErrors` (flat `string[]`), `order` (with `id`, `number`, `customerName`, `email`, `amountPaid`, `currency`), `product` (split out: `id`, `url`, `year`, `season`, `sport`, `day`, `division`, `week1Start..week5Start`), and `estimate` (`original`, `storeCredit`).                                                                                                                                                                                                                                                                             | User direction — Pydantic adds value at the trust boundary (incoming JSON validation); for outgoing responses the backend already controls the shape, so a `BaseModel` is overhead. Plain dicts also avoid having to map every nested layer into a separate Pydantic class.                                      |
| D29 | **Picker primitives (callback-derived action ids, page-size default) live in `views/_shared/picker_modal.ts`.** No refund-specific picker constants. The picker exposes `pickerActionIds(callbackId)` returning `{ radioPrefix, nextPage, prevPage }` with each id formed as `${callbackId}__<suffix>`, and a single `PICKER_ENTRIES_PER_PAGE_DEFAULT` constant. Per-flow input blocks (test-mode toggle, post-to-channel input) and their block / action ids stay alongside the calling function (e.g. `functions/send_request_for_eval.ts`); they are passed to `pickerModal()` via the existing `extraInputBlocks` parameter and are NOT part of the picker's public surface.                                                                                                                                                                                                                                                                                                                                                          | User direction — same generic-and-parameterized principle as the BARS API client (D22) and the approve-modal builder (D23). Picker primitives are reusable across any future "pick one of N items" flow; refund-flow concerns stay in the refund flow.                                                           |
| D30 | **NO `ExecuteService` orchestrator.** Controllers handle the cancel-then-refund branching directly because the if/else is ~10 lines. Orchestration logic stays in the `POST /refunds/create` controller, NOT in a separate service. Each domain service (`ShopifyRefundService`) produces reusable inputs and delegates to the canonical Shopify client. The `backend/modules/refunds/services/execute_service.py` file is deleted from the design entirely; Stage 5's deliverables list reflects the controller-handles-branching pattern.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | User direction — "there should NOT be an execute service. absolutely not. all shopify execution is handled centrally through the client with reusable inputs from each service, using utils and ONLY reusable utils that are business-agnostic." Ten-line branching does not justify a class.                    |
| D31 | **Shopify cancel/refund execution uses the existing `client.run(schema.x.y.z, **kwargs)`pattern verbatim** — verified against`backend/lib/clients/shopify-client/shop_client.py`and existing successful call sites at`backend/legacy/services/refunds/service.py:187,225,238`and`backend/legacy/services/orders/service.py:45`. NO constructor-based mutation invocations (e.g. NO `OrderCancelMutation(input=...)`), NO typed input dataclasses, NO new client primitives, NO `MutationOp(...)` direct construction in calling code. Reusable input-builders (`\_build_refund_transactions_for_shopify`, `\_build_store_credit_refund_methods`, `\_parent_capture_txn`) stay as static methods on `ShopifyRefundService`BUT must be **business-agnostic helpers** that take primitives and return primitives. Genuinely-business-agnostic utilities (e.g. money formatting) move to`backend/utils/`. The deprecated `backend/lib/clients/shopify_client/` (underscore) directory is NOT referenced for any client-instrumentation logic. | User direction — "shopify.execute(OrderCancelMutation(input=...)) seems wrong, please check existing structure of the gql client and don't invent any new structures or methodology that doesn't already exist." Anchoring on the existing pattern preserves the canonical client as the single source of truth. |

---

## Testing Strategy

All tests are deferred to a later stage. Each stage's design section lists
planned test file names only. No tests are built as part of design; no
per-test prescriptions are made. The "no PBT" decision (D8) is a strategy
commitment, not a per-test prescription.

---

## Dependencies

- Existing: `deno-slack-sdk`, `slack-block-builder` (Slack), `fastapi`,
  `pydantic`, `httpx`, `sgqlc` (backend), `google-sheets-api`, Shopify Admin GQL.
- New: none. All needed libraries are already in `deno.jsonc` /
  `backend/pyproject.toml`.
