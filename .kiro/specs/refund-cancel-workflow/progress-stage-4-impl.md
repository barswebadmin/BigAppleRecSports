# Stage 4 Implementation Progress

- [x] 4.1 Move wire-shape types api.ts → types.ts; delete api.ts; relocate normalizeRefundOrCredit
- [x] 4.2 Refactor eval_blocks.ts to consume RefundRequestEval
- [x] 4.3 Remove legacy Lambda receiver flow
- [x] 4.4 Verification (deno check + deno lint pass)
- [x] 4.5 Update Stage 4 design's TODO note

## Files created

- `slack-apps/registrations/domain/refund/normalizers.ts` — new home for `normalizeRefundOrCredit`.

## Files modified

- `slack-apps/registrations/domain/refund/types.ts` — wire-shape types (`ValidateRefundSheetRowRef`, `ValidateRefundRequest`, `TierEstimate`, `RefundEvalOrder`, `RefundEvalProduct`, `RefundEvalEstimate`, `RefundRequestEval`, `RefundRestockTo`, `CreateRefundRequest`, `ShopifyUserError`, `CancelOutcome`, `RefundOutcome`, `CreateRefundResponse`) inlined; the temporary re-export shim is gone. `RefundSheetEntry.refundOrCredit` doc updated to point at `normalizers.ts`. Legacy Lambda-shape types kept (deleted in 4.3).
- `slack-apps/registrations/functions/send_request_for_eval.ts` — imports `normalizeRefundOrCredit` from `../domain/refund/normalizers.ts` and `ValidateRefundRequest` from `../domain/refund/types.ts`.
- `slack-apps/registrations/clients/bars_api/client.ts` — header comment updated: refund call sites build request bodies inline against types in `domain/refund/types.ts` and call `post<T>` directly; no `domain/refund/api.ts` wrapper.
- `slack-apps/registrations/views/refund/eval_blocks.ts` — auditied against design § 4.b–§ 4.g; the stale `"sent to Lambda"` string in the approved-decision renderer flipped to `"sent to BARS API"`. Header doc-comment lost the `RefundEvaluationPayload` reference (the type is gone in 4.3). Everything else (signature, field reads, parenthesized natural-English copy, silent-on-empty week-schedule context, `validationSummaryBlocks` adapter call, dropped Refund-to/Already-Refunded/Notes/SMS) already matched the design.
- `slack-apps/registrations/domain/refund/types.ts` — legacy Lambda-flow types (`RefundType`, `OrderActionRef`, `RefundEstimate`, `RefundTransaction`, `RefundEvaluationPayload`) deleted. Now exports only the new sheet-driven flow domain (`RefundTo`, `RefundSheetEntry`, `RefundSheetData`, `RefundDecision`) plus the `/refunds/validate` and `/refunds/create` wire shapes. Top-of-file docstring rewritten to describe the two layers and drop the now-stale Lambda-payload framing. `RefundDecision.dryRun` doc updated to describe `/refunds/create` rather than the Lambda.
- `slack-apps/registrations/manifest.ts` — removed the broken `EvaluateRefundRequestWorkflow` import (the file did not exist), removed `EvaluateRefundRequestWorkflow` from the `workflows` array, and dropped `REFUND_PROCESS_DOMAIN` from the imports + `OUTGOING_DOMAINS` list (Deno no longer dispatches to the refund Lambda).
- `slack-apps/registrations/config/store.ts` — deleted `REFUND_PROCESS_URL` and `REFUND_PROCESS_DOMAIN` constants and the `// ── Lambda endpoints ──` section. The `REFUND_PROCESS_URL` env var stays in `.env`; the app no longer reads it.
- `slack-apps/registrations/views/refund/approve_modal.ts` — header doc-comment updated: legacy "downstream importers (orchestrator, post_refund_evaluation function)" wording replaced with "the Stage 5 submission handler that POSTs to `/refunds/create`". `ApproveModalMeta` doc replaced "post to the Lambda" with "POST `/refunds/create`".

## Files deleted

- `slack-apps/registrations/domain/refund/api.ts` (4.1).
- `slack-apps/registrations/shared/action_ref.ts` (4.3) — its sole consumer was `OrderActionRef` (legacy Lambda-flow type), which was deleted from `types.ts`. No other importer in the workspace.

## Notes

- Pre-existing baseline: `domain/refund/orchestrator.ts`, `domain/refund/action_requests.ts`, `functions/post_refund_evaluation.ts`, `triggers/evaluate_refund_request.ts`, and `workflows/evaluate_refund_request.ts` were already absent from the working tree. `manifest.ts` still imports `EvaluateRefundRequestWorkflow` from a missing path; that broken import is removed in Substage 4.3.
- `eval_blocks.ts` had already been refactored to consume `RefundRequestEval`. Substage 4.2 audits the file against § 4.b–§ 4.g and tightens any remaining drift; it is not a from-scratch rewrite.
- 4.1 verification: `deno check` on the four touched files passes.
- 4.3: deleted `shared/action_ref.ts` as an additional consumer (not enumerated in the prompt) — it was orphaned the moment `OrderActionRef` left `types.ts`. Per the prompt's "if doing so breaks something I haven't enumerated, document the additional deletion in the progress notes and proceed" rule.
- 4.4 verification: `deno check **/*.ts` and `deno lint` both pass with zero errors across all 80 files.

## Final status

COMPLETED

## Planned tests (file names only — per Stage 4 design § 4.h)

- `slack-apps/registrations/tests/views/refund/eval_blocks_test.ts`

## A1 Substage checkpoints (verification re-run)

The previous Stage-4 impl run already landed every A1 substage; this
re-run confirms each step is in its final state and re-runs the build
gates. Each checkpoint below records the verification touchpoint, not
a from-scratch save.

- [x] A1.1 Move types from api.ts → types.ts — saved at 2026-06-20T22:25:13Z (api.ts already deleted; full wire-shape type set lives in types.ts; verified by `list_directory` + `grep` for `domain/refund/api`)
- [x] A1.2 Update Stage 1 importers of moved types — saved at 2026-06-20T22:25:13Z (no remaining `from "../domain/refund/api"` imports anywhere; verified by repo-wide grep)
- [x] A1.3 Refactor eval_blocks.ts function signature + imports — saved at 2026-06-20T22:25:13Z (signature is `buildRefundEvalBlocks(refundEval: RefundRequestEval, decision?: RefundDecision)`; imports `{RefundDecision, RefundEvalProduct, RefundRequestEval, TierEstimate}` from `../../domain/refund/types.ts`)
- [x] A1.4 Refactor eval_blocks.ts body (field paths) — saved at 2026-06-20T22:25:13Z (orderField/leagueField/playerField/header/two-col/estimate all read from `refundEval.{order,product,estimate}.*`; `buildNotFoundBlocks` deleted)
- [x] A1.5 Drop refund-to / already-refunded / notes / SMS lines — saved at 2026-06-20T22:25:13Z (no references to `p.refund_to|p.total_refunded|p.refundable_balance|p.notes|p.first_name|p.last_name|p.phone|p.email|p.season_start_date|p.season_week_resolved|p.estimated_refund_to_original|p.estimated_store_credit|p.validation_passed|p.warnings|p.order_total|p.order_found|p.is_cancelled` in the file)
- [x] A1.6 Week-schedule context + remove warning-on-absence — saved at 2026-06-20T22:25:13Z (`seasonScheduleContext` returns `null` when all five `weekNStart` fields are null; renderer is silent — backend owns the diagnostic via `validationErrors[]`)
- [x] A1.7 User-facing strings (no markdown italics) — saved at 2026-06-20T22:25:13Z (`(incl. processing fee)` and `(no payment on order)` have no surrounding `_..._`)
- [x] A1.8 Validation summary inline adapter — saved at 2026-06-20T22:25:13Z (call site builds `{validation_passed: refundEval.isValid, warnings}` where `warnings` falls back to `["Validation failed"]` for the degenerate `isValid=false && validationErrors=[]` case)
- [x] A1.9 deno check + deno lint pass — saved at 2026-06-20T22:25:13Z (`deno check **/*.ts` exit 0; `deno lint` checked 80 files exit 0)
- Final status A1: COMPLETED

## A2 Sync barrier

Agent B's actual progress file is `progress-stages-5-6-7-design.md`
(the prompt referenced `progress-stage-5-design.md`, which does not
exist). The line `Stage 5 — REFRESHED — saved at 2026-06-20T19:50:46Z`
is present and the file's preamble explicitly designates that line as
the sync signal. A3 unblocked.
