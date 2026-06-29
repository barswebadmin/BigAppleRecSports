# Design — Stage 7: Slack final-confirmation card renderer [DETAILED]

> Parent: see [design.md](./design.md) for the overall feature design and
> Stages 1–6.

> Stage 7 is the Slack-side renderer + handler refactor that consumes
> `CreateRefundResponse` (built by Stage 5 § 5.d, documented by Stage 6
> § 6.b–§ 6.e) to render the final-confirmation card after the operator
> approves. It is the bookend to Stage 4 (which refactored
> `eval_blocks.ts` for the validate-response branch). Stage 7 finishes
> the post-execute branch of the same renderer.

> **Sub-agent prerequisites.** Before starting Stage 7:
>
> - Stage 5 § 5.k retroactive cleanup is complete:
>   `domain/refund/api.ts` is GONE; wire types live in
>   `domain/refund/types.ts`; `RefundRestockTo` is the four-lane string
>   union; `RESTOCK_OPTIONS` is the four-lane set;
>   `ApproveModalValues.restock` is `RestockAction | undefined`.
> - Stage 5 has built `POST /refunds/create` and returns
>   `CreateRefundResponse` per Stage 5 § 5.c / Stage 6 § 6.b.
> - Stage 4 has refactored the no-decision branch of `eval_blocks.ts`
>   to consume `RefundRequestEval`.

---

## 7.a — File inventory (concrete)

| File                                                                                                                                                                                           | Action                                                                                                                                                                                                                                                                                                                   |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `slack-apps/registrations/views/refund/eval_blocks.ts`                                                                                                                                         | EXTEND — add a final-confirmation rendering path that reads `CreateRefundResponse`. New exported function `buildRefundResultBlocks(result, decision)` lives next to the existing `buildRefundEvalBlocks(refundEval, decision?)`.                                                                                         |
| `slack-apps/registrations/domain/refund/orchestrator.ts` (or wherever the modal-submit handler lives — confirm at start of execution; current Stage 1 spec places it in the orchestrator file) | UPDATE — after the BARS API call to `POST /refunds/create` returns, build the final card from `CreateRefundResponse` field-by-field via `buildRefundResultBlocks(...)`; call `chat.update` on the original review-card message with the new blocks. On HTTP failure, post an error context block via `chat.postMessage`. |
| `slack-apps/registrations/domain/refund/types.ts`                                                                                                                                              | READ ONLY — Stage 5 § 5.k.4 moved `CreateRefundResponse`, `CancelOutcome`, `RefundOutcome`, `RefundDecision` etc. here; Stage 7 imports them.                                                                                                                                                                            |
| Generic Slack helpers (`shared/slack/blocks.ts`, etc.)                                                                                                                                         | READ ONLY — Stage 7 reuses `section`, `context`, `divider`, `mrkdwnField`, `header`. No new helpers.                                                                                                                                                                                                                     |

> **No new files** are created by Stage 7. The renderer extends
> `eval_blocks.ts` with one new exported function. No new HTTP wrapper
> functions, no `domain/refund/api.ts` resurrection, no new
> directories.

> **Helper inventory (read first).** Before editing `eval_blocks.ts`,
> confirm these private helpers exist and stay refund-card-local:
> `truncate(text, max)`, `numericId(gid)`, `titleCase(s)`,
> `adminUiLinkField(title, segment, label, id)`, `orderField(p)`,
> `leagueField(p)`, `playerField(p)`, `estimateLine(label, est)`,
> `decisionLine(d)`. Stage 7 ADDS a new exported renderer function
> alongside them; the existing helpers are not modified.

---

## 7.b — Type signatures (renderer entry points)

```typescript
// slack-apps/registrations/views/refund/eval_blocks.ts (Stage 7 addition)

import type {
  CancelOutcome,
  CreateRefundResponse,
  RefundDecision,
  RefundOutcome,
} from "../../domain/refund/types.ts";
import {
  type Block,
  context,
  divider,
  header,
  mrkdwnField,
  section,
} from "../../shared/slack/blocks.ts";
import { formatMoney } from "../../shared/text/strings.ts";
import { BARS_URLS } from "../../config/store.ts";

/**
 * Build the final-confirmation card from a backend CreateRefundResponse plus
 * the operator's decision. Pure function; no Slack API calls. Renders into
 * the same review message via chat.update.
 *
 * Decision (Stage 7 § 7.b): one new exported function rather than a branch
 * on `buildRefundEvalBlocks` — the validate-eval card and the post-execute
 * card have different field sets and rendering logic; merging them into
 * one function would require a discriminator parameter and conditional
 * branches that obscure both paths.
 */
export function buildRefundResultBlocks(
  result: CreateRefundResponse,
  decision: RefundDecision,
): Block[];
```

### Why a separate function (not a branch on `buildRefundEvalBlocks`)

The validate-eval card (Stage 4) reads from `RefundRequestEval` —
order / product / estimate / validation. The post-execute card
(Stage 7) reads from `CreateRefundResponse` — `cancel`, `refund`,
`errors`, plus the operator's `RefundDecision`. The field sets
overlap only on `decision` (which both branches show). Merging into
a single function requires a discriminator parameter that tells the
function which shape it's dealing with — that's two `if (refundEval)
{ … } else if (result) { … }` branches inside one function body, plus
shared decision-line logic. Two narrowly-scoped functions are easier
to read, easier to test, and easier to evolve independently.

---

## 7.c — Field-by-field rendering map

| Block group       | Source field                                                       | Treatment                                                                                                                                                                                                                                                                              |
| ----------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Header            | `decision.by` (Slack user id) and `decision.status`                | `:white_check_mark: Approved by <@${decision.by}>` when `decision.status === "approved"`; `:no_entry: Denied by <@${decision.by}>` otherwise (denial path is rare on this card — denials normally short-circuit before the BARS API call — but the renderer covers it for robustness). |
| Cancel outcome    | `result.cancel`                                                    | When non-null: `Order cancelled — Job <${BARS_URLS.admin_ui}/jobs/${numericId(jobId)}\|${numericId(jobId)}> · ${jobDone ? "completed" : "in progress"}`. When null: section omitted.                                                                                                   |
| Refund outcome    | `result.refund`                                                    | When non-null: `Refund issued — ${formatMoney(amount, currency)} via ${currency === "STORE_CREDIT" ? "store credit" : "original payment method"} · created ${createdAt}`. When null: section omitted.                                                                                  |
| Errors            | `result.errors[]`                                                  | When non-empty: `:warning: *Errors from Shopify*` header + bullet list of `error.message` lines (one context line per error). When empty: section omitted.                                                                                                                             |
| Decision metadata | `decision.{amount, refundType, restock, sendNotification, dryRun}` | Single context block: `Approved: ${formatMoney(decision.amount)} via ${decision.refundType}${decision.restock ? ` · restock to ${decision.restock}` : ""}${decision.sendNotification ? " · notify customer" : ""}${decision.dryRun ? " · DRY RUN" : ""}`.                              |

> **No `_..._` markdown italic syntax** around inline annotations
> (per the Stage 4 convention). Plain bold (`*...*`) is allowed for
> headers like `:warning: *Errors from Shopify*`; italics around
> field values are NOT used.

> **`numericId(gid)` is the existing private helper** in
> `eval_blocks.ts` that strips the `gid://shopify/Job/` /
> `gid://shopify/Refund/` prefix and returns the numeric tail. It
> already exists from the validate-eval branch (Stage 4); Stage 7
> reuses it on the cancel/refund GIDs.

> **`formatMoney(amount, currency)`** is reused from
> `slack-apps/registrations/shared/text/strings.ts`. For
> `currency === "STORE_CREDIT"`, the function falls back to dollar
> formatting (BARS is USD-only); the `via store credit` suffix in
> the rendering map disambiguates.

---

## 7.d — Validation / error surfacing

When `result.ok === false || result.errors.length > 0`, the renderer
emits a prominent error section ABOVE the cancel/refund outcome
sections so the operator sees the failure first. The cancel section
is still rendered if `result.cancel !== null` (partial-success case
from Stage 6 § 6.c's contract — cancel ok, refund userError), so the
operator sees what DID succeed alongside what failed.

```typescript
const blocks: Block[] = [];

// Header (always first).
blocks.push(headerBlock(decision));

// Error surfacing (above the outcome sections when present).
if (!result.ok || result.errors.length > 0) {
  blocks.push(section(":warning: *Refund could not be completed*"));
  for (const err of result.errors) {
    const fieldHint = err.field
      ? ` (field: ${Array.isArray(err.field) ? err.field.join(".") : err.field})`
      : "";
    blocks.push(context(`• ${err.message}${fieldHint}`));
  }
  blocks.push(divider());
}

// Cancel outcome (if present, even on partial-success failure).
if (result.cancel !== null && result.cancel !== undefined) {
  blocks.push(cancelOutcomeBlock(result.cancel));
}

// Refund outcome (if present).
if (result.refund !== null && result.refund !== undefined) {
  blocks.push(refundOutcomeBlock(result.refund));
}

// No-op fallback (cancel=false, refund=false, no errors).
if (
  result.cancel == null &&
  result.refund == null &&
  result.errors.length === 0
) {
  blocks.push(
    context("(no action taken — neither cancel nor refund was requested)"),
  );
}

// Decision metadata (always last).
blocks.push(decisionMetaBlock(decision));

return blocks;
```

The private builders (`headerBlock`, `cancelOutcomeBlock`,
`refundOutcomeBlock`, `decisionMetaBlock`) are local to
`eval_blocks.ts` — no exports. They exist purely to keep the
top-level `buildRefundResultBlocks` body readable.

---

## 7.e — Branch matrix

The seven rows of the post-execute card. Each row maps to a distinct
`if` branch in `buildRefundResultBlocks`; the branch matrix is
verifiable by inspection.

| `body.cancel` | `body.refund` | `result.ok`                      | Card sections rendered                        |
| ------------- | ------------- | -------------------------------- | --------------------------------------------- |
| true          | true          | true                             | header · cancel · refund · decision-meta      |
| true          | true          | false (cancel ok, refund failed) | header · cancel · errors · decision-meta      |
| true          | false         | true                             | header · cancel · decision-meta               |
| true          | false         | false                            | header · errors · decision-meta               |
| false         | true          | true                             | header · refund · decision-meta               |
| false         | true          | false                            | header · errors · decision-meta               |
| false         | false         | true                             | header · "no-op" context line · decision-meta |

> Rows where `body.cancel === true && result.ok === false` AND
> `result.cancel === null` (i.e. the cancel mutation itself failed)
> render via the global 422 handler — the BARS API call throws and
> the Slack handler's failure path posts an error message instead
> of updating the review card. See § 7.f. So the table above only
> covers the rows the renderer actually receives via a 200 response.

---

## 7.f — `chat.update` integration with the existing review-card path

The existing approval-modal submit handler (Stage 1 placed it in
`functions/send_request_for_eval.ts` for the validate path; Stage 5
§ 5.m wires the create-refund call) currently calls
`buildRefundEvalBlocks(refundEval, decision)` to render the
post-decision review card from the Stage 4 path. Stage 7 changes the
post-execute path to:

```typescript
import type {
  CreateRefundRequest,
  CreateRefundResponse,
  RefundDecision,
} from "../../domain/refund/types.ts";
import { buildRefundResultBlocks } from "../views/refund/eval_blocks.ts";

const createRequest: CreateRefundRequest = {
  /* assembled from view.private_metadata + extracted modal values */
};

try {
  const result = await barsApi.post<CreateRefundResponse>({
    endpoint: "/refunds/create",
    body: createRequest,
  });

  const decision: RefundDecision = {
    status: "approved",
    by: body.user.id,
    amount: values.amount,
    refundType: createRequest.refundTo,
    approveAction: values.action,
    restock: values.restock, // RestockAction | undefined; omitted when no lane chosen
    sendNotification: values.sendNotification,
  };

  const finalBlocks = buildRefundResultBlocks(result, decision);

  await client.chat.update({
    channel: meta.channel,
    ts: meta.message_ts,
    text: `Refund result for ${decision.refundType}`,
    blocks: finalBlocks,
  });
} catch (err) {
  const message = err instanceof Error ? err.message : String(err);
  await client.chat.postMessage({
    channel: meta.channel,
    blocks: [context(`:x: Refund execution failed: ${message}`)],
    text: `Refund execution failed: ${message}`, // fallback for clients without blocks
  });
  // Original review card stays in its pre-decision state so the
  // operator can fix the issue and retry.
}
```

The orchestrator no longer reuses `buildRefundEvalBlocks` for the
post-decision card; the result card is its own renderer
(`buildRefundResultBlocks`). The post-decision branch of
`buildRefundEvalBlocks` (which Stage 4 introduced and which renders
"Approved by @user — sent to backend" while the BARS call is in
flight) stays — Stage 4 owns it. Stage 7 only refactors the
post-EXECUTE rendering path, which fires AFTER the BARS API
returns.

### Why `chat.update` on success and `chat.postMessage` on failure

The success path replaces the original review-card content with the
post-execute card (showing approval header + cancel/refund outcome).
The failure path leaves the original card UNTOUCHED so the operator
can fix the issue and retry the approval — overwriting the card with
an error message would lose the eval context the operator needs to
retry. The error message is posted as a separate message to the
same channel.

---

## 7.g — Stage 7 deliverables checklist

- [ ] `buildRefundResultBlocks(result, decision)` exists in
      `views/refund/eval_blocks.ts` and is exported. Type signature
      matches § 7.b verbatim.
- [ ] `domain/refund/orchestrator.ts` (modal-submit handler) calls
      `buildRefundResultBlocks` after the BARS API response and
      `chat.update`s the review message. Verifiable by
      `grep -n "buildRefundResultBlocks" slack-apps/registrations/domain/refund/orchestrator.ts`
      returning at least one match.
- [ ] On HTTP failure (BARS API throws), the handler calls
      `chat.postMessage` instead of `chat.update`. Verifiable by
      inspecting the catch block in the modal-submit handler — see
      § 7.f.
- [ ] No backend code constructs Slack Block Kit (D12 — verifiable
      by `! grep -rn "slack_sdk.blocks\|block_builders" backend/`
      returning no matches).
- [ ] No `RefundEvaluationPayload` references in the Stage 7 code
      path. Verifiable by
      `! grep -rn "RefundEvaluationPayload" slack-apps/registrations/`
      returning no matches (Stage 4 retired the type; Stage 7 must
      not resurrect it).
- [ ] User-facing strings: no `_..._` markdown-italic syntax around
      inline annotations. Verifiable by inspecting the strings in
      `buildRefundResultBlocks` — only `*bold*` is used, never
      `_italic_`.
- [ ] Branch matrix in § 7.e is verifiable by inspection — each row
      maps to a distinct `if` branch in `buildRefundResultBlocks`.
      Reviewer reads the function body alongside the table.
- [ ] No new HTTP wrapper functions added. The BARS API client
      (`clients/bars_api/client.ts`) is the ONLY HTTP layer.
      Verifiable by
      `! grep -rn "fetch\\(" slack-apps/registrations/domain/refund/`
      returning no matches and
      `! grep -rn "REFUND_PROCESS_URL" slack-apps/registrations/domain/refund/ slack-apps/registrations/views/refund/ slack-apps/registrations/functions/send_request_for_eval.ts`
      returning no matches in the new Stage 7 code path.
- [ ] No `response.blocks` or `result.blocks` field reads anywhere
      in `slack-apps/registrations/`. The backend never returns
      Block Kit; the Slack app builds Block Kit locally from the
      `CreateRefundResponse` field reads. Verifiable by
      `! grep -rn "response\\.blocks\\|result\\.blocks" slack-apps/registrations/`
      returning no matches.
- [ ] Stage 7 design file is TypeScript-only — no Python code in
      scope. Outdated Python typing conventions are not an issue
      here (constraint trivially satisfied; flagged here to keep
      deliverables-checklist symmetry with Stages 5 / 6).
- [ ] `deno check slack-apps/registrations/` passes.
- [ ] `deno lint slack-apps/registrations/` passes.

---

## 7.h — Tests planned (deferred — file names only)

All tests are deferred to a later stage. Build these in a later stage:

- `slack-apps/registrations/tests/views/refund/eval_blocks_result_test.ts`
  — covers all 7 rows of the § 7.e branch matrix; verifies the field-
  by-field rendering map in § 7.c; verifies the error-section position
  per § 7.d.
- `slack-apps/registrations/tests/domain/refund/orchestrator_submit_test.ts`
  — covers the `chat.update` integration on success and the
  `chat.postMessage` integration on failure; verifies the request body
  is constructed correctly across all branches (cancel-only, refund-
  only, cancel + refund; `restockTo` omitted vs. present).

---

## Cross-references

- **Depends on:** Stage 1 (orchestrator infrastructure: the modal,
  the BARS API client, the `domain/refund/types.ts` foundation),
  Stage 4 (review-card refactor sets the field-import pattern Stage
  7 mirrors), Stage 6 (`CreateRefundResponse` shape — § 6.b for the
  TypedDicts, § 6.c for the field-by-field contract, § 6.e for the
  property-validation invariants the renderer relies on).
- **Can run in parallel with:** none — Stage 7 is the final
  assembly; everything else feeds into it. (Stage 7 can BEGIN as
  soon as Stage 5 § 5.k completes and Stage 6 § 6.b is published,
  but its full scope requires Stage 5's `POST /refunds/create` to be
  live in a deployable state.)
- **Blocks:** none.

---

## 7.todo — Orchestrator TODOs (apply to design.md when accumulating)

These items are sub-agent feedback for the orchestrator; they affect
`design.md` and are out of scope for the Stage 7 implementation
sub-agent itself.

1. **Update the architecture sequence diagram** in `design.md`'s
   "Architecture" section. The diagram's last two messages currently
   show:

   ```
   API-->>Slack: {ok, cancel, refund, errors[]}  (controller-built dict; NOT Pydantic, NOT Block Kit)
   Slack-->>Op: post final confirmation message (Slack builds Block Kit locally)
   ```

   The "post final confirmation message" arrow should be more
   specifically `chat.update` on success / `chat.postMessage` on
   failure, mirroring Stage 7 § 7.f. Optional refinement; the
   existing text is not wrong, just less precise.

2. **Confirm `REFUND_PROCESS_URL` retirement.** Stage 5 § 5.h's
   deliverables list mentions updating
   `domain/refund/action_requests.ts` to point at
   `POST /refunds/create` "when `BARS_API_URL` is set; Lambda path
   stays as fallback". Stage 7's deliverables fully retire the
   Lambda path in the new code path (no `REFUND_PROCESS_URL`
   references). The orchestrator should reconcile: Stage 5 leaves
   the fallback in place for safety; Stage 7 removes it from the new
   code path once the backend endpoint is verified in production. If
   the fallback is needed during a rollout window, Stage 7's
   deliverable is relaxed to "no `REFUND_PROCESS_URL` references in
   the new Stage 7 code path" — the legacy file stays untouched
   until cutover.

3. **No new decisions.** Stage 7 introduces no new design decisions;
   it consumes Stage 5's endpoint and Stage 6's response-shape
   contract verbatim.
