# Registrations App — Restructure Plan

Scope: `slack-apps/registrations/` only. Cross-repo refactor work tracked elsewhere.

**Status:** Phase 1 in progress.

## Working conventions

- **No barrels. No back-compat re-exports.** When code moves, every import path breaks; fix
  consumers in the same PR. We are not preserving any existing public surface.
- **Above-the-fold layout in every touched file.** Inside any file that's partially refactored,
  refactored / newly arrived code sits at the top under a marker; not-yet-refactored holdovers sit
  below under a second marker. When everything's refactored, drop the markers.
  ```ts
  // ─── refactored ──────────────────────────────────────────────────────────
  // new and relocated code (top-down by call-graph order)

  // ─── pending (to be hoisted or deleted) ─────────────────────────────────
  // unrefactored holdovers
  ```
- **Combine, split, rename freely.** No weight on consistency with existing structure. Every move is
  an opportunity to fix shape, not just location.
- **Each phase = one PR.** Acceptance criteria below must pass before the phase's checkbox flips.
  Tests stay green throughout (`deno task test` clean).
- **Going-away Shopify direct-post code is never refactored** — only quarantined in `legacy/` and
  eventually deleted.

## Target end-state layout

```
slack-apps/registrations/
  manifest.ts, workflows/, triggers/      # SDK declarations (untouched)
  functions/                              # thin Slack workflow handlers (~50-150 lines each)
  config/
    env.ts                                # readEnv, envOr, ENV
    store.ts                              # STORE, ORG_DOMAIN, BARS_URLS, productPageUrl, shopifyCustomerAdminUrl
    slack.ts                              # SLACK_LINK_TEXT, slackLink, tagSlackMember, ACTION_OPTIONS, ENTRIES_PER_PAGE
    refunds.ts                            # REFUND_*_CHANNEL, REFUND_PROCESS_URL, REFUND_DRY_RUN, resolveRefundChannel, OUTGOING_DOMAINS
    workflows.ts                          # WORKFLOWS registry, getWorkflowSheet
    capture.ts                            # DROPDOWN_CAPTURE_CONFIG, CHECKBOX_CAPTURE_CONFIG
  domain/
    league/
      types.ts                            # League type
      key.ts                              # build/parse/leagueFromKey/formatLeagueKey
      format.ts                           # league + division + product handle + tag formatters
      catalog.ts                          # LEAGUE_DATA, getLeague, getDaysForSport, getDefaultLeagueForChannel, WEEKDAY_ORDER, compareWeekday, CURRENT_YEAR, CURRENT_SEASON
      selection_state.ts                  # modal state for league picker
    waitlist/
      types.ts                            # WaitlistEntry, LeagueWaitlist, LeagueWaitlists, EmailLookupEntry, status constants
      action.ts                           # WaitlistAction
      action_result.ts                    # ActionResult (moved out of display)
      parse.ts                            # parseWaitlistRows
      sheet.ts                            # fetchWaitlists (with statusColumnIndex folded in)
      admit_email.ts                      # email body builder
      row_planning.ts                     # planAdmitShopifyTag, planAdmitEmail, initActionResult, buildRowProcessing
      row_execution.ts                    # executeShopifyForRow, executeEmailForRow, executeRowProcessing
      dry_run_steps.ts                    # toDryRunSteps + builders + htmlToText + buildEmailCopy
      display.ts                          # formatEntryTitle, formatActionBullet, buildWaitlistResultMessage, buildWaitlistConfirmModal, formatSubmittedTimestamp
      modal.ts                            # buildListView, buildModalTitle, buildEmptyWaitlistView, buildPopulatedWaitlistView, SPORT_ABBR, isContacted
      status_format.ts                    # formatStatusTimestamp(now), statusText
    refund/
      types.ts                            # RefundEstimate, RefundTransaction, RefundEvaluationPayload
      lambda_requests.ts                  # buildCancelOrderRequest, buildCreateRefundRequest, executeLambdaRequest
      eval_blocks.ts                      # buildRefundEvalBlocks, RefundDecision
      approve_modal.ts                    # buildApproveModal, ApproveModalMeta
      orchestrator.ts                     # runPostRefundEvaluation
  shared/
    slack/
      blocks.ts                           # section/header/divider/context
      diagnostics.ts                      # formatDiagnostic
      list_modal.ts                       # generic paginated list modal
      dry_run.ts                          # generic dry-run preview
      modal_state.ts                      # captureModalStateWithInputs, extractModalState
      workflow.ts                         # NEW: makeWorkflowCompleter, executionId, processorUserId, completeWithEmpty
    http/
      prepared_request.ts                 # PreparedRequest, maskSecret, maskHeaders
    google/
      client.ts                           # GoogleClient, SheetTab, CellUpdate, columnToLetter
      gmail.ts                            # gmail wrappers
      email_message.ts                    # EmailMessage type
    text/
      strings.ts                          # capitalize, titlecase, formatMoney
      phone.ts                            # normalizePhone, isValidPhone, phonesMatch
      date.ts                             # parseDate, formatDate, toISOString, nowISO
  legacy/
    shopify_client/                       # to be deleted when migration completes
  tests/                                  # mirrors domain/* structure
  RESTRUCTURE-PLAN.md                     # this doc
```

**Dependency direction:** `functions/` → `domain/` → `shared/` → `config/`. Never reversed. No
cross-domain imports between `domain/X/` and `domain/Y/` except shared types.

## Phase status legend

`[ ]` open · `[~]` in progress · `[x]` done · `[abandoned]` decided not to do

## Decisions preserved from old plans

- **Logger factory abandoned.** One-line
  `const log = (fn, ...args) => console.log(\`[prefix:${fn}]\`, ...args)` at the top of files stays.
  Revisit only when prefix scheme needs richer payloads.
- **`WaitlistEntry.league: League` is the canonical league carrier.** No flat `sport/day/division`
  on entries.
- **`formatStatusTimestamp(now: Date = new Date())` is injectable.** Call sites pin the clock once
  per run.
- **`HandleRefundRequest` retired.** The only refund evaluation path is GAS → lambda → Slack.

---

## Phase 1 — Quarantine going-away code

**Status:** `[ ]` open

**Goal:** isolate the Deno Shopify direct-post code so no later phase wastes effort refactoring it.
Establish `legacy/` as the "do not touch" bucket.

- [ ] Create `legacy/shopify_client/` and move `lib/clients/shopify/` contents into it (flatten the
      `types/` subdir).
- [ ] Delete `lib/exports/export_product_orders.ts` — it's a CLI duplicate of
      `scripts/shopify/export_product_orders.py` (which is the canonical version per the file's own
      header). Zero in-app consumers.
- [ ] Update import paths in the 2 consumer files: `functions/handle_waitlist_actions.ts` and
      `functions/get_league_selections_from_modal.ts`.
- [ ] Add `legacy/README.md` stating "Anything in here is going away. Do not refactor. Move out only
      via planned migration."
- [ ] `deno task verify` clean. All 6 tests pass.

**Acceptance:** `lib/clients/shopify/` no longer exists. `legacy/shopify_client/` and
`legacy/README.md` exist. No behavior change.

---

## Phase 2 — Split `config.ts`

**Status:** `[ ]` open

**Goal:** retire the 547-line god-module by splitting `config.ts` into 6 focused files under
`config/`. No barrel, no back-compat shim — every consumer's import line changes.

- [ ] Create `config/env.ts` with `readEnv`, `envOr`, `ENV`, `Env` type.
- [ ] Create `config/store.ts` with `STORE`, `STORE_MYSHOPIFY_DOMAIN`, `ORG_DOMAIN`, `BARS_URLS`,
      `GOOGLE_API`, `shopifyCustomerAdminUrl`, `productPageUrl`.
- [ ] Create `config/slack.ts` with `SLACK_LINK_TEXT`, `slackLink`, `tagSlackMember`,
      `ACTION_OPTIONS`, `ENTRIES_PER_PAGE`, `DEFAULT_GMAIL_SENDER`.
- [ ] Create `config/refunds.ts` with `REFUND_TEST_CHANNEL`, `REFUND_REVIEW_CHANNEL`,
      `REFUND_PROCESS_URL`, `REFUND_PROCESS_DOMAIN`, `REFUND_DRY_RUN`, `resolveRefundChannel`,
      `OUTGOING_DOMAINS`.
- [ ] Create `config/workflows.ts` with `WORKFLOWS`, `WorkflowName`, `WorkflowConfig`,
      `getWorkflowSheet`.
- [ ] Create `config/capture.ts` with `DROPDOWN_CAPTURE_CONFIG`, `CHECKBOX_CAPTURE_CONFIG`.
- [ ] Provisionally place LEAGUE_DATA + helpers in `config/leagues_provisional.ts` (relocated to
      `domain/league/catalog.ts` in Phase 4).
- [ ] Delete `config.ts`.
- [ ] Update every consumer's imports.
- [ ] `deno task verify` clean.

**Acceptance:** `config.ts` is gone. Every import references a specific `config/*.ts` file. No
barrel.

---

## Phase 3 — Establish `shared/`

**Status:** `[ ]` open

**Goal:** relocate every domain-agnostic primitive into `shared/`, with the dependency direction now
visibly enforced.

- [ ] Move `lib/slack/{blocks,diagnostics,list_modal,dry_run}.ts` → `shared/slack/`.
- [ ] Move `lib/slack/state.ts` → `shared/slack/modal_state.ts` (rename: the old name was too
      generic).
- [ ] **NEW** `shared/slack/workflow.ts` — extract `makeWorkflowCompleter`, `executionId`,
      `processorUserId` from `functions/handle_waitlist_actions.ts`.
- [ ] Move `lib/clients/prepared_request.ts` → `shared/http/prepared_request.ts`.
- [ ] Move `lib/clients/google/{client,gmail}.ts` → `shared/google/`; flatten
      `types/email_message.ts` to `shared/google/email_message.ts`.
- [ ] Split `utils/formatters.ts`: generic text helpers → `shared/text/strings.ts`; phone helpers →
      `shared/text/phone.ts`; league-specific formatters stay until Phase 4.
- [ ] Move `utils/date_utils.ts` → `shared/text/date.ts`.
- [ ] Delete `lib/slack/`, `lib/clients/prepared_request.ts`, `lib/clients/google/`.
- [ ] Update every consumer's imports.
- [ ] `deno task verify` clean.

**Acceptance:** `shared/` holds every domain-agnostic primitive. Workflow plumbing duplicated across
`functions/*.ts` is consolidated in `shared/slack/workflow.ts`.

---

## Phase 4 — Establish `domain/league/`

**Status:** `[ ]` open

**Goal:** every league-shaped concept lives in `domain/league/`. Consolidates 6 currently scattered
files.

- [ ] Move `types/league.ts` → `domain/league/types.ts`.
- [ ] Move `lib/waitlists/league_key.ts` → `domain/league/key.ts`.
- [ ] Move `lib/leagues/selection_state.ts` → `domain/league/selection_state.ts`.
- [ ] Move league formatters from `utils/formatters.ts` → `domain/league/format.ts`.
- [ ] Move league catalog from `config/leagues_provisional.ts` → `domain/league/catalog.ts`.
- [ ] Delete `config/leagues_provisional.ts`, `lib/leagues/`, `types/league.ts`; assess
      `utils/formatters.ts`.
- [ ] Audit and collapse division formatter duplicates per WAITLIST-HANDLER-REFACTOR §1d.
- [ ] Update every consumer's imports.
- [ ] `deno task verify` clean.

**Acceptance:** every league import resolves to `domain/league/`.

---

## Phase 5 — Establish `domain/waitlist/`

**Status:** `[ ]` open

**Goal:** every waitlist concept lives in `domain/waitlist/`. Completes the file-level extractions
deferred from the handler refactor we did this session.

- [ ] Flatten `lib/waitlists/handlers/` → move into `domain/waitlist/` as `types.ts` and `parse.ts`.
- [ ] Move `lib/waitlists/waitlist_action.ts` → `domain/waitlist/action.ts`.
- [ ] Move `lib/waitlists/sheet_service.ts` → `domain/waitlist/sheet.ts`. **Fold
      `resolveStatusColumnIndex` into `fetchWaitlists`** — one HTTP call; `LeagueWaitlists` gains
      `statusColumnIndex: number`.
- [ ] Move `lib/waitlists/admit_email.ts` → `domain/waitlist/admit_email.ts`.
- [ ] Move `lib/waitlists/display.ts` → `domain/waitlist/display.ts`. Extract `ActionResult` →
      `domain/waitlist/action_result.ts`.
- [ ] Move `formatStatusTimestamp` + `statusText` from `functions/update_waitlist_spreadsheet.ts` →
      `domain/waitlist/status_format.ts`.
- [ ] Extract from `functions/handle_waitlist_actions.ts`:
  - Row planning → `domain/waitlist/row_planning.ts`.
  - Row execution → `domain/waitlist/row_execution.ts`.
  - Dry-run step builders → `domain/waitlist/dry_run_steps.ts`.
  - Modal builders → `domain/waitlist/modal.ts`.
- [ ] Eliminate the `as unknown as Record<string, unknown>` cast in `captureModalStateWithInputs` by
      tightening capture helpers' signatures in `shared/slack/modal_state.ts`.
- [ ] `functions/handle_waitlist_actions.ts` becomes ~150 lines of pure SDK wiring + the
      orchestrator.
- [ ] Update test imports in `tests/waitlist_dry_run_test.ts` and `tests/waitlist_resolve_test.ts`.
- [ ] Delete `lib/waitlists/`.
- [ ] `deno task verify` clean. All 6 tests pass.

**Acceptance:** `lib/waitlists/` gone. `domain/waitlist/` exists with the 11 files in target layout.
Handler ≤200 lines. Unsound cast removed.

---

## Phase 6 — Establish `domain/refund/`

**Status:** `[ ]` open

**Goal:** every refund concept lives in `domain/refund/`. In-place cleanup of
`post_refund_evaluation.ts` first, then extract.

- [ ] **In-place cleanup of `functions/post_refund_evaluation.ts`**: split orchestrator into named
      phases, separate eval/approval/deny handlers, adopt `shared/slack/workflow.ts`, fix any no-arg
      side-effecting functions.
- [ ] Move `types/evaluation_payload.ts` → `domain/refund/types.ts`. Delete `types/` if empty.
- [ ] Move `lib/refunds/lambda_requests.ts` → `domain/refund/lambda_requests.ts`.
- [ ] Move `lib/slack/refund_eval_blocks.ts` → `domain/refund/eval_blocks.ts`.
- [ ] Move `lib/slack/refund_approve_modal.ts` → `domain/refund/approve_modal.ts`.
- [ ] Extract orchestrator body → `domain/refund/orchestrator.ts`.
- [ ] `functions/post_refund_evaluation.ts` becomes ~50 lines of SDK wiring.
- [ ] Update test imports in `tests/refund_*_test.ts`.
- [ ] Delete `lib/refunds/`.
- [ ] `deno task verify` clean.

**Acceptance:** `domain/refund/` exists with 5 files. `lib/refunds/` and `lib/slack/refund_*` gone.
Handler is thin wiring.

---

## Phase 7 — In-place cleanup of remaining `functions/*.ts`

**Status:** `[ ]` open

**Goal:** apply the in-place decomposition pattern (named-phase orchestrator + single-concern
helpers + above-the-fold layout + injected dependencies) to every remaining handler.

- [ ] `functions/get_league_selections_from_modal.ts` (239 L) — apply the pattern. Extract reusable
      league-picker bits to `domain/league/` if they cross the bar.
- [ ] `functions/get_league_waitlist_selection.ts` (133 L) — apply the pattern.
- [ ] `functions/fetch_current_waitlists.ts` (70 L) — small cleanup pass.
- [ ] `functions/update_waitlist_spreadsheet.ts` — small cleanup pass.
- [ ] `functions/resolve_waitlist_order.ts` (78 L) — small cleanup pass.
- [ ] Adopt `shared/slack/workflow.ts` plumbing in every handler.
- [ ] `deno task verify` clean.

**Acceptance:** every `functions/*.ts` file is thin SDK wiring + orchestrator delegation. No file

> 200 lines. No duplicated `executionId`/`completeSuccess` blocks.

---

## Phase 8 — Retire `lib/`, `utils/`, `types/`, finalize docs

**Status:** `[ ]` open

**Goal:** the parent dirs that were "miscellaneous code" buckets no longer exist.

- [ ] Verify `lib/`, `utils/`, `types/` are empty; delete the empty directories.
- [ ] Reorganize `tests/` to mirror `domain/` (subfolders as needed). Update import paths.
- [ ] Replace `README.md` (currently the boilerplate Deno starter README) with a real README: app
      purpose, directory layout, dependency rules, "do not touch legacy/", run/test/deploy
      instructions.
- [ ] Update `slack-apps/README.md` directory map if it references old paths.
- [ ] Mark this `RESTRUCTURE-PLAN.md` complete at the top.
- [ ] `deno task verify` clean.

**Acceptance:** top-level dirs are exactly `config/`, `domain/`, `shared/`, `legacy/`, `functions/`,
`workflows/`, `triggers/`, `tests/` + SDK files + README. README accurately describes the
architecture.

---

## Risks + watchouts

- **Phase 2 is the highest import-churn phase.** ~50 files touch config. Land it alone.
- **Phase 5 has the most behavioral risk** (extracts from the file with the only behavioral test
  coverage of the orchestrator). Run `tests/waitlist_dry_run_test.ts` repeatedly during the phase.
- **Phase 6's in-place cleanup of `post_refund_evaluation.ts` comes BEFORE its extractions**,
  mirroring the waitlist-handler order.
- **Cross-phase ordering is strict.** Phase 4 needs Phase 2's interim home for league code. Phase 5
  needs `shared/` settled (Phase 3). Don't reorder.
