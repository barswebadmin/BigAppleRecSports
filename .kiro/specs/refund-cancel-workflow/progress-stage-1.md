# Stage 1 Progress

## Substages

- [x] 1.1 Generic primitives (bars_api/client, columns, picker_modal, approve_modal)
- [x] 1.2 Refund-domain types and loaders
- [x] 1.3 Refund approve modal thin-caller refactor
- [x] 1.4 Workflow + trigger + function
- [x] 1.5 Verification (deno check + deno lint)
- [x] 1.6 Slash-command wiring note

## Files created

- slack-apps/registrations/clients/bars_api/client.ts (1.1)
- slack-apps/registrations/shared/google/columns.ts (1.1)
- slack-apps/registrations/views/\_shared/picker_modal.ts (1.1)
- slack-apps/registrations/views/\_shared/approve_modal.ts (1.1)
- slack-apps/registrations/domain/refund/sheet_loader.ts (1.2)
- slack-apps/registrations/domain/refund/api.ts (1.2)
- slack-apps/registrations/functions/send_request_for_eval.ts (1.4)
- slack-apps/registrations/triggers/start_refund_eval.ts (1.4)
- slack-apps/registrations/workflows/validate_refund_request.ts (1.4)

## Files modified

- slack-apps/registrations/domain/refund/types.ts (1.2 — appended Stage 1
  types: `RefundTo`, `RefundSheetEntry`, `RefundSheetData`. Existing
  webhook-flow types kept verbatim; nothing renamed/removed.)
- slack-apps/registrations/views/refund/approve_modal.ts (1.3 — refactored
  to a thin caller of `views/_shared/approve_modal.ts`. Renamed
  `APPROVE_MODAL_CALLBACK_ID = "approve_refund_modal"` →
  `REFUND_APPROVAL_MODAL_CALLBACK_ID = "refund_approval_modal"`. Block /
  action ids re-exported under their original names so existing handler
  bindings stay compatible.)
- slack-apps/registrations/functions/post_refund_evaluation.ts (1.3 —
  updated import + view-submission registration to use the new constant
  name.)
- slack-apps/registrations/manifest.ts (1.4 — registered
  `ValidateRefundRequestWorkflow`.)
- slack-apps/registrations/config/workflows.ts (1.4 — added
  `default: envOr("SLACK_CHANNEL__REFUNDS__DEFAULT", "#joe-test")` to the
  refund channels block; widened the `WorkflowConfig.channels.static`
  variant to allow the new optional `default` field.
  `REFUND_TEST_CHANNEL` and `REFUND_REVIEW_CHANNEL` were left untouched
  per the design directive that the existing webhook flow keeps using
  them.)
- slack-apps/registrations/shared/slack/channel.ts (1.4 — appended
  `resolveRefundChannel({ requested, env })`; the existing `resolveChannel`
  is left in place for the webhook flow.)

## Notes

- 1.1: `views/_shared/picker_modal.ts` is built as a sibling to
  `shared/slack/list_modal.ts`, NOT a re-export. Documented inline:
  `list_modal.ts` is a per-row dropdown picker (each row has its own
  independent action+state); the new picker is a single radio group whose
  selection is mutually exclusive across all paginated rows. The two
  patterns share only low-level block primitives.
- 1.2: existing `domain/refund/types.ts` already exports webhook-flow types
  (`RefundType`, `RefundEvaluationPayload`, `OrderActionRef`, `RefundDecision`,
  etc.) imported by the existing webhook flow. New Stage 1 types appended;
  no existing exports renamed or removed. `RefundTo` and `RefundType` are
  semantically identical aliases — the legacy flow keeps `RefundType`, new
  Stage 1 code uses `RefundTo`.
- 1.3: `views/refund/pick_row_modal.ts` was checked and does NOT exist —
  the design's "delete if exists" instruction was a no-op.
- 1.4: the orchestrator function (`send_request_for_eval.ts`) wires up
  state capture, picker view, pagination, radio selection, test-mode
  toggle, and post-to-channel input per design § 1b. The actual
  `validateRefund(barsApi, …)` HTTP call + `refund_approval_modal` push
  is staged behind a Stage 1b TODO — the validate-request body is built
  on submit but not yet sent (Slack-side surface is in place; backend
  contract remains design-only until Stage 2 lands the route). For now
  the submit handler posts a follow-up message naming the picked row to
  the resolved channel and completes the workflow step.
- 1.5: `deno check **/*.ts` passes (88 files, 0 errors). `deno lint`
  passes (88 files, 0 errors). For good measure `deno fmt` was applied
  to normalize indentation back to the deno.jsonc-declared 4-space
  setting (auto-formatter on save had drifted toward 2-space in the
  newly-created files). Existing test suite (`deno test --allow-read`)
  continues to pass: 10/10 green.
- 1.6: the slash command `/eval-refund-request` is registered via the
  Slack CLI at deploy time (`slack triggers create` against
  `triggers/start_refund_eval.ts`). The workflow file
  (`workflows/validate_refund_request.ts`) and the trigger file compile
  cleanly; the manifest now lists `ValidateRefundRequestWorkflow`. No
  manifest-level slash-command declaration is needed in Run-on-Slack
  apps — the Shortcut trigger plus CLI registration is the canonical
  path. README update + actual `slack triggers create` invocation are
  out of scope for Stage 1 implementation work; deploy-time wiring is
  documented in the Stage 1 design.

## Final status

COMPLETED
