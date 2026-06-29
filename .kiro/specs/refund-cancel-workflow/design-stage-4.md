# Design — Stage 4: Validation response shape (Slack-side renderer refactor) [DETAILED]

> Parent: see [design.md](./design.md) for the overall feature design and Stages 1-3.

> The wire shape is fixed in Stage 2 (`RefundRequestEval` — see § 2.b in
> design.md). It is a plain Python dict / `TypedDict` constructed by the
> FastAPI controller — NOT a Pydantic model (D28). Stage 4's actual work
> is on the Slack side: the existing
> `slack-apps/registrations/views/refund/eval_blocks.ts` is refactored to
> consume the new dict shape directly (`RefundRequestEval` from
> `domain/refund/types.ts`), retiring the older Lambda-payload
> (`RefundEvaluationPayload`) field reads.

## Backend response — structured, not Pydantic (recap)

`RefundRequestEval` (Stage 2 § 2.b) is the contract. It's a TypedDict with
camelCase keys constructed manually by the FastAPI controller — Pydantic is
reserved for incoming external request bodies only (D28). The Slack-side
TypeScript mirror lives in `slack-apps/registrations/domain/refund/types.ts`
(types-only — no HTTP signature logic; the domain-agnostic API wrapper is
`clients/bars_api/client.ts`).

```python
# Sketch — see backend/modules/refunds/models/estimate.py for the canonical shape.
RefundRequestEval = TypedDict("RefundRequestEval", {
    "ok": bool,
    "isValid": bool,
    "validationErrors": Optional[List[str]],   # OPTIONAL — flat string[]; absent on happy path
    "order":   OrderInfo,    # { id, number, customerName, email, amountPaid, currency }
    "product": ProductInfo,  # { id, url, year, season, sport, day, division, week1Start..week5Start }
    "estimate": {            # EstimateBlock
        "original":    TierEstimate,  # { amount, percentage, tierLabel, appliedProcessingFee, notes }
        "storeCredit": TierEstimate,
    },
}, total=False)
```

**Hard rule** (D12 / D28): no `blocks: list[dict]` field, no
`backend/modules/slack/block_builders/`, no `eval_payload_builder.py`, no
`build_validate_blocks(...)` / `build_*_payload(...)` on the backend, and
no Pydantic `BaseModel` for outgoing shapes. The Slack app reads
`refundEval.estimate.original.amount`, `refundEval.product.week1Start`, etc.
directly into its own block builders.

---

## 4.a — Files touched (concrete inventory)

| File                                                        | Action                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `slack-apps/registrations/views/refund/eval_blocks.ts`      | **REFACTOR** — type signature + body migrated from `RefundEvaluationPayload` to `RefundRequestEval`.                                                                                                                                                         |
| `slack-apps/registrations/domain/refund/types.ts`           | **READ ONLY** — Stage 4 imports `RefundRequestEval`, `RefundEvalOrder`, `RefundEvalProduct`, `RefundEvalEstimate`, `TierEstimate`, `RefundDecision` from here. (See note below on the Stage 1 fix-up that physically relocates these types into `types.ts`.) |
| `slack-apps/registrations/shared/slack/blocks.ts`           | **READ ONLY** — `validationSummaryBlocks` is reused via an inline adapter object (see § 4.d). No change to the helper itself; the helper remains a generic `ValidationSummarySource`-shaped consumer used by other flows.                                    |
| `slack-apps/registrations/shared/slack/block_kit_button.ts` | **READ ONLY** — `blockKitButton(...)` reused as-is for the action row.                                                                                                                                                                                       |
| `slack-apps/registrations/shared/text/strings.ts`           | **READ ONLY** — `formatMoney(...)` reused as-is.                                                                                                                                                                                                             |
| `slack-apps/registrations/config/store.ts`                  | **READ ONLY** — `BARS_URLS.admin_ui` reused for the order/product admin-deep-link helpers.                                                                                                                                                                   |

> **Type-relocation note (orchestrator TODO).** `RefundRequestEval`,
> `RefundEvalOrder`, `RefundEvalProduct`, `RefundEvalEstimate`, and
> `TierEstimate` previously lived in
> `slack-apps/registrations/domain/refund/api.ts` — the domain-coupled
> file the user wanted gone. **Done in this stage.** Types live in
> `domain/refund/types.ts`; `domain/refund/api.ts` was deleted; the
> `normalizeRefundOrCredit` helper moved to
> `domain/refund/normalizers.ts`. The domain-agnostic
> `clients/bars_api/client.ts` is the only HTTP wrapper; refund call
> sites build the request body inline against the `types.ts` shapes and
> call `post<T>` directly.

No new files. No new directories. The refactor extracts no helpers — the
existing renderer's small private helpers (`numericId`, `titleCase`,
`adminUiLinkField`, etc.) stay co-located inside `eval_blocks.ts` because
they're refund-card-specific. If a future flow needs the same admin-link
formatting it can lift them into `views/_shared/`, but that's out of scope
for Stage 4.

> **Helper inventory (read first).** Before editing the file, confirm the
> following private helpers exist and stay refund-card-local:
> `truncate(text, max)`, `numericId(gid)`, `titleCase(s)`,
> `adminUiLinkField(title, segment, label, id)`, `orderField(p)`,
> `leagueField(p)`, `playerField(p)`, `estimateLine(label, est)`,
> `buildNotFoundBlocks(p)`, `decisionLine(d)`. Stage 4 rewrites the bodies
> of these helpers to read from the new field paths (per § 4.c) but keeps
> their names + signatures backwards-compatible for any internal call sites
> that already use them.

---

## 4.b — Type signatures

```typescript
// slack-apps/registrations/views/refund/eval_blocks.ts

import { toTitleCase } from "@std/text/unstable-to-title-case";
import { BARS_URLS } from "../../config/store.ts";
import type {
  RefundDecision,
  RefundEvalOrder,
  RefundEvalProduct,
  RefundRequestEval,
  TierEstimate,
} from "../../domain/refund/types.ts";
import { formatMoney } from "../../shared/text/strings.ts";
import { blockKitButton } from "../../shared/slack/block_kit_button.ts";
import {
  type Block,
  context,
  divider,
  header,
  mrkdwnField,
  section,
  validationSummaryBlocks,
} from "../../shared/slack/blocks.ts";

export const APPROVE_ACTION_ID = "approve_refund";
export const DENY_ACTION_ID = "deny_refund";
export const CONTACT_ACTION_ID = "contact_player";

/**
 * Refund eval review-card block builder.
 *
 * Pure function — no Slack API calls. Renders from the FastAPI backend's
 * `RefundRequestEval` (camelCase wire shape; see Stage 2 § 2.b) plus an
 * optional reviewer decision.
 *
 * Consumes ONLY field paths under `refundEval.order.*`, `refundEval.product.*`,
 * `refundEval.estimate.*`, `refundEval.isValid`, and `refundEval.validationErrors`. The
 * old Lambda payload (`RefundEvaluationPayload`) is no longer accepted —
 * see § 4.f for the migration note.
 */
export function buildRefundEvalBlocks(
  refundEval: RefundRequestEval,
  decision?: RefundDecision,
): Block[];
```

`RefundDecision` (Stage 1's existing pure-data reviewer-decision struct in
`domain/refund/types.ts`) is unchanged; it carries `{status, by, amount?,
refundType?, dryRun?, approveAction?, restock?, sendNotification?}`. Stage 4
re-uses it verbatim for the post-decision context line.

> **`approvedBy` field-name alignment.** The pre-existing `RefundDecision`
> uses `by: string` (Slack user id of the approver). On the wire,
> `CreateRefundRequest` (Stage 5 § 5.b) calls the same field `approvedBy`.
> Both are the same value; no renaming inside `RefundDecision` is needed
> for Stage 4.

---

## 4.c — Field-by-field rendering map

The mapping below replaces every field read in the existing
`buildRefundEvalBlocks` body. Stage 4 walks the function top-to-bottom and
swaps the read for the new path.

| Block group                       | Old field path (`RefundEvaluationPayload`)                          | New field path (`RefundRequestEval`)                                                                                                                                                                                                                                                                                                                          |
| --------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Header — customer name**        | `${p.first_name} ${p.last_name}`                                    | `refundEval.order.customerName`                                                                                                                                                                                                                                                                                                                               |
| **Header — order number**         | `p.order_number`                                                    | `refundEval.order.number`                                                                                                                                                                                                                                                                                                                                     |
| **Two-col § — Player line**       | `p.first_name`, `p.last_name`, `p.email`, `p.phone`                 | `refundEval.order.customerName`, `refundEval.order.email` (no phone in new shape; line drops the `<sms:…>` segment)                                                                                                                                                                                                                                           |
| **Two-col § — League line**       | `p.sport`, `p.day`, `p.division`, `p.product_id`                    | `refundEval.product.sport`, `refundEval.product.day`, `refundEval.product.division`, `refundEval.product.id`                                                                                                                                                                                                                                                  |
| **Two-col § — Refund to**         | `p.refund_to`                                                       | _Not in `RefundRequestEval`._ Stage 4 drops the "Refund to" field from the review card; the operator picks it on the approval modal (Stage 1 sets the picker default from the sheet). **Decision (Stage 4 § 4.c):** the line is dropped — the renderer signature stays single-arg (`buildRefundEvalBlocks(refundEval, decision?)`); no `refundTo` second arg. |
| **Two-col § — Order link**        | `p.order_number`, `p.order_id`                                      | `refundEval.order.number`, `refundEval.order.id`                                                                                                                                                                                                                                                                                                              |
| **Two-col § — Total Amount Paid** | `p.order_total`                                                     | `refundEval.order.amountPaid`                                                                                                                                                                                                                                                                                                                                 |
| **Two-col § — Already Refunded**  | `p.total_refunded` (rendered when `> 0`)                            | _Not in `RefundRequestEval`._ Stage 4 drops the "Already Refunded" line. (Q8 below: surface partial-refund state on the card?)                                                                                                                                                                                                                                |
| **Notes §**                       | `p.notes`                                                           | _Not in `RefundRequestEval`._ Stage 4 drops the Notes section. (The validate request body still echoes `notes` but the response does not — see Stage 2 § 2.b.)                                                                                                                                                                                                |
| **Estimate header**               | `section("*Estimated Refund Due*")`                                 | Unchanged — static markdown.                                                                                                                                                                                                                                                                                                                                  |
| **Estimate reasoning context**    | `p.season_start_date`, `p.season_week_resolved`                     | Replaced with a context line built from the `product` week schedule (see § 4.c sub-table below). When all `weekNStart` are `null` the renderer is silent — the backend owns the diagnostic via `validationErrors[]` (see C5 note below the code block).                                                                                                       |
| **Estimate — original**           | `p.estimated_refund_to_original` (`RefundEstimate`)                 | `refundEval.estimate.original` (`TierEstimate` — `{amount, percentage, tierLabel, appliedProcessingFee, notes}`)                                                                                                                                                                                                                                              |
| **Estimate — store credit**       | `p.estimated_store_credit` (`RefundEstimate`)                       | `refundEval.estimate.storeCredit` (`TierEstimate`)                                                                                                                                                                                                                                                                                                            |
| **Validation summary**            | `{validation_passed: p.validation_passed, warnings: p.warnings}`    | Inline adapter `{validation_passed: refundEval.isValid, warnings: refundEval.validationErrors ?? []}` (see § 4.d).                                                                                                                                                                                                                                            |
| **Approval line**                 | `decision?.{status, by, amount, refundType, dryRun, approveAction}` | Unchanged — `RefundDecision` shape is reused as-is.                                                                                                                                                                                                                                                                                                           |
| **Action buttons (no decision)**  | `value: p.order_number` for Approve/Deny                            | `value: refundEval.order.number` for both buttons.                                                                                                                                                                                                                                                                                                            |

> **Note — `refundEval.order.currency`.** The field is the ISO 4217
> currency code of the order's payment (e.g. `"USD"`). Sourced by the
> backend from `order.total_price_set.shop_money.currency_code` — see
> Stage 2 § 2.c. The renderer uses this only as the
> `formatMoney(amount, currency)` second arg; for USD it's a no-op (the
> existing `formatMoney` formats USD by default). BARS is USD-only today;
> the field is preserved on the wire for forward-compatibility but the
> card always renders dollars.

### Week schedule context line (replaces `season_start_date` reasoning)

The existing card emits a single context line — `Season start: 2025-01-15`
(or `:warning: Season dates not found on product` when null). The new shape
surfaces the full 5-week schedule, so Stage 4 emits a single-line context
that lists whichever weeks parsed. **Crucially, the renderer does NOT
synthesize a `:warning: Season dates not found` line from the absence of
`weekNStart` values.** When all five starts are null/missing, the
week-schedule context line is omitted entirely. If the backend wants to
surface "season dates could not be parsed", it adds an explicit string to
`refundEval.validationErrors[]` (e.g.
`"Season dates could not be parsed from product description"`); the
renderer surfaces it through the existing `validationSummaryBlocks(...)`
adapter — same path as every other backend-emitted validation error.

```typescript
function seasonScheduleContext(product: RefundEvalProduct): Block | null {
  const starts = [
    product.week1Start,
    product.week2Start,
    product.week3Start,
    product.week4Start,
    product.week5Start,
  ];
  const labels = starts
    .map((s, i) => (s ? `W${i + 1} ${s}` : null))
    .filter((s): s is string => s !== null);
  if (labels.length === 0) {
    // Renderer is silent — backend owns the diagnostic via validationErrors.
    return null;
  }
  return context(`Season schedule: ${labels.join(" · ")}`);
}
```

> **C5 note — validation errors are explicit, not inferred.** The
> `:warning: Season dates not found` diagnostic is the backend's
> responsibility (Stage 2 — emit it as a string in `validationErrors[]`
> when `SeasonDates.from_html(...)` returns no usable start). Stage 4 does
> not synthesize the warning from absence; the renderer's only signal that
> something is wrong is the `validationErrors[]` list itself.

### `TierEstimate` ↔ `RefundEstimate` field-by-field

The `estimateLine(label, est)` helper changes input shape:

| Old `RefundEstimate` field  | New `TierEstimate` field                | Renderer treatment                                                                                                                                                          |
| --------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `est.success`               | _gone_                                  | **Decision (Stage 4 § 4.c):** always render. `tierLabel` and `amount` are always present in `TierEstimate`, so there is no "unhappy" branch to gate on.                     |
| `est.amount`                | `est.amount`                            | Rendered via `formatMoney(...)`.                                                                                                                                            |
| `est.percentage` (nullable) | `est.percentage` (number)               | Always rendered as ` (${pct}%)` — no null path.                                                                                                                             |
| `est.has_processing_fee`    | `est.appliedProcessingFee > 0`          | Renders ` (incl. processing fee)` when `appliedProcessingFee > 0`.                                                                                                          |
| `est.timing` (string)       | `est.tierLabel` (string)                | Always rendered inline next to the amount. The reasoning context block (§ 4.c week-schedule sub-table) carries the timing context now, so the per-tier line keeps it terse. |
| `est.no_payment`            | `est.notes.includes("no_payment_made")` | Renders `(no payment on order)` suffix.                                                                                                                                     |
| `est.message`               | _gone_                                  | The flat `refundEval.validationErrors` list carries any backend-side message.                                                                                               |

---

## 4.d — Validation-error rendering

`refundEval.validationErrors` is a flat `string[]` (no structured `mismatches[]`,
no `email_matched_against` / `first_name_matched_against` / etc.). The
renderer adapts the new shape to the existing generic
`validationSummaryBlocks(v: ValidationSummarySource)` helper at the call
site — the helper itself is **untouched** so other flows that consume the
generic `{validation_passed, warnings: string[]}` shape keep working.

```typescript
// inside buildRefundEvalBlocks, replacing the existing `validationSummaryBlocks(p)` call
...validationSummaryBlocks({
  validation_passed: refundEval.isValid,
  warnings: refundEval.validationErrors ?? [],
}),
```

The helper renders:

- A single section `:white_check_mark: *Validation passed* — no warnings`
  when `isValid === true && (validationErrors ?? []).length === 0` (this
  IS the validation-passed indicator — see § 4.e).
- Otherwise, a header section `:warning: *N warning(s)*` followed by one
  bullet section per error string.

### When `isValid === false` but `validationErrors` is empty

This is a degenerate state (the backend should never produce it) but the
renderer should still surface a visible cue. Stage 4 wraps the adapter so
the warnings list is at minimum `["Validation failed"]` when isValid is
false and no errors are supplied:

```typescript
const warnings = refundEval.validationErrors?.length
  ? refundEval.validationErrors
  : (refundEval.isValid ? [] : ["Validation failed"]);
...validationSummaryBlocks({ validation_passed: refundEval.isValid, warnings }),
```

---

## 4.e — Validation-passed indicator

The renderer reuses the existing pattern emitted by `validationSummaryBlocks`:

> `:white_check_mark: *Validation passed* — no warnings`

This fires exactly when both:

1. `refundEval.isValid === true`, AND
2. `(refundEval.validationErrors ?? []).length === 0`.

No additional badge, header glyph, or dedicated context block is added by
Stage 4. The single green-check section is the entire indicator and matches
the existing behavior of the legacy webhook flow's review card.

---

## 4.f — Removed wire fields (the renderer no longer reads these)

This is a full refactor. `eval_blocks.ts` has one input shape —
`RefundRequestEval`. The previous `RefundEvaluationPayload` consumer is
gone; there is no compatibility branch and no second behavioral path.

After Stage 4, `eval_blocks.ts` no longer reads any of the following
top-level Lambda-payload fields (kept here as a migration-diff reference
for reviewers comparing the old card source to the new):

- `validation_passed`, `warnings`, `email_matched_against`,
  `first_name_matched_against`, `last_name_matched_against`
  (validation now flows through `refundEval.isValid` + `refundEval.validationErrors`)
- `season`, `season_start_date`, `season_week_resolved`
  (season context now flows through `refundEval.product.season` and the
  `weekNStart` schedule)
- `sport`, `day`, `division`, `product_id`, `product_title`
  (now `refundEval.product.{sport,day,division,id,url}` — and the renderer reads
  `url` directly when it needs the product page link, instead of constructing
  a URL from a numeric id)
- `order_number`, `order_id`, `order_total`, `order_found`,
  `total_refunded`, `refundable_balance`, `is_cancelled`
  (now `refundEval.order.{number,id,amountPaid}`; `order_found` is gone — the
  validate response always returns an `order` block on `ok=true`,
  `order_found=false` paths surface as `isValid=false` with a validation
  error string instead)
- `transactions`, `currency_code`
  (the backend re-fetches transactions on `/refunds/create`; not shown on
  the review card)
- `error`, `notes`, `phone`, `email`, `first_name`, `last_name`,
  `refund_to`, `is_test`
  (none surface on the review card; the operator's chosen `refundTo`
  appears on the approval modal instead)

Deno does not call the refund Lambda after this migration. The legacy
`RefundEvaluationPayload` type and any code paths that consumed it are
removed in a Stage 5 cleanup substage (see § 5.x in `design-stage-5.md`);
Stage 4 itself only owns the new renderer.

**Migration note for any reviewer reading the diff:**

> Stage 4 is a full refactor of `views/refund/eval_blocks.ts`. The
> renderer accepts `RefundRequestEval` and ONLY `RefundRequestEval`. There
> is no compatibility branch; the previous Lambda-payload consumer is
> removed in this commit.

---

## 4.g — Stage 4 deliverables checklist

- [ ] `views/refund/eval_blocks.ts` accepts `RefundRequestEval` (typed
      import from `domain/refund/types.ts`) instead of the old
      `RefundEvaluationPayload` shape.
- [ ] All block groups read from the new field paths per § 4.c (header,
      two-column section, estimate, validation, approval line, action
      buttons).
- [ ] Week-schedule context line replaces the old `season_start_date`
      reasoning per § 4.c sub-table.
- [ ] `validationErrors` is rendered as a `validationSummaryBlocks` call
      with the inline adapter object per § 4.d (the generic helper itself
      is NOT modified).
- [ ] `refundEval.isValid` (combined with empty `validationErrors`) drives the
      green-check validated-indicator per § 4.e.
- [ ] **Drops** the "Refund to" two-col field, the "Already Refunded"
      line, the Notes section, and the SMS phone link, because none of
      those fields exist on `RefundRequestEval`.
- [ ] No `refundEval.blocks`, no `refundEval.season` (top-level), no `refundEval.validation`
      (nested object), no `refundEval.warnings` (top-level) field reads
      anywhere in `slack-apps/registrations/`.
- [ ] No backend file imports `slack_sdk.blocks`; no
      `backend/modules/slack/block_builders/` directory exists. (D12 —
      verifiable by `grep -rn "slack_sdk.blocks\|block_builders" backend/`
      returning zero matches.)
- [ ] No backend code constructs a Pydantic model for the outgoing
      validate response. The controller's `response_model` is `dict` (or
      omitted entirely). (D28 — verified at Stage 2 boundary; Stage 4 only
      consumes the dict.)
- [ ] `deno check slack-apps/registrations/` passes.
- [ ] `deno lint slack-apps/registrations/` passes.

---

## 4.h — Tests planned (deferred — file names only)

All tests are deferred to a later stage. Build these in a later stage:

- `slack-apps/registrations/tests/views/refund/eval_blocks_test.ts`

---

## Cross-references

- **Depends on:** Stages 2, 3 (the validate response shape and Shopify
  service wrapper must exist before Stage 4 wires Block Kit to consume them).
  The `RefundRequestEval` TypeScript mirror lives at
  `slack-apps/registrations/domain/refund/types.ts` (types-only) — Stage 4
  imports it without modification.
- **Can run in parallel with:** Stage 5 — once the wire contract for
  `RefundRequestEval` is fixed (Stage 2), Stage 4 (Slack-side review-card
  refactor) and Stage 5 (cancel + refund execution) proceed independently.
- **Blocks:** none directly. Stage 7 indirectly depends on the same Block
  Kit refactor here because it reuses the helpers in `eval_blocks.ts` to
  re-render the card with a `decision` line; that re-use is preserved by
  keeping `RefundDecision` unchanged.
