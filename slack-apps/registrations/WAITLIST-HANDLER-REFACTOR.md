# Waitlist Handler Refactor Plan

Decompose the 658-line `functions/handle_waitlist_actions.ts` god function into
focused, reusable modules. Cross-cutting extractions first (shared by waitlist,
refund, and webhook workflows), then the handler-specific decomposition.

**Scope:** `slack-apps/registrations/` — waitlist processing workflow and its
shared dependencies.

---

## Stage 1: Cross-Cutting Extractions

Shared infrastructure that benefits every workflow, not just waitlists. Each
extraction is independently shippable.

### 1a: League key utilities

**Problem:** 7+ ad-hoc `leagueKey.split("|")` / `` `${sport}|${day}|${division}` ``
scattered across files.

**Sites:**
- `handle_waitlist_actions.ts:93,295` — `toLeague()`, submit handler
- `get_league_waitlist_selection.ts:115`
- `resolve_waitlist_order.ts:41`
- `lib/waitlists/handlers/sheet_parser.ts:66`
- `lib/waitlists/display.ts:86`
- `config.ts:421`

**Action:**
- [ ] Create `utils/league_key.ts` with:
  - `toLeagueKey(league: League): string` — canonical `sport|day|division`
  - `parseLeagueKey(key: string): { sport: string; day: string; division: string }`
  - `leagueFromKey(key: string): League` — calls `parseLeagueKey` + adds `CURRENT_YEAR`/`CURRENT_SEASON`
- [ ] Replace all 7+ ad-hoc split/join sites
- [ ] Delete `handle_waitlist_actions.ts:91-105` (`toLeague`, `entryLeague`)

**Success:** Zero raw `split("|")` calls remain. League key construction is
tested in one place.

---

### 1b: Block Kit primitives

**Problem:** `plainText`, `mrkdwnSection`, `divider`, `contextBlock` redefined
in 4 files independently.

**Sites:**
- `lib/slack/list_modal.ts:59-71`
- `lib/slack/dry_run.ts:17-22`
- `lib/slack/refund_eval_blocks.ts:24-27`
- `lib/slack/refund_approve_modal.ts` (inline)

**Action:**
- [ ] Create `lib/slack/blocks.ts` exporting `plainText`, `mrkdwnSection`, `section`, `heading`, `divider`, `contextBlock`
- [ ] Replace all 4 local definitions with imports from `blocks.ts`

**Success:** One import path for Block Kit primitives across all Slack UI code.

---

### 1c: Logger factory

**Problem:** `const log = (fn: string, ...args: unknown[]) => console.log(...)` copy-pasted
in 5+ files with different prefix strings.

**Sites:**
- `handle_waitlist_actions.ts:54`
- `lib/waitlists/admit_email.ts:16`
- `lib/clients/shopify/customer_ops.ts:26`
- `lib/clients/shopify/product_ops.ts:9`
- `lib/clients/shopify/client.ts:151,163`

**Action:**
- [ ] Create `utils/log.ts`: `export const makeLogger = (prefix: string) => (fn: string, ...args: unknown[]) => console.log(\`[${prefix}:${fn}]\`, ...args);`
- [ ] Replace all 5+ hand-rolled loggers

**Success:** Consistent log prefix format. Swappable if structured logging is
added later.

---

### 1d: Consolidate division label formatters

**Problem:** 3+ functions that format a division string for display, 2 of which
are exact duplicates.

**Sites:**
- `utils/formatters.ts:9` — `formatDivision()` → `"WTNB+ Division"` / `"Open Division"`
- `utils/formatters.ts:13` — `formatDivisionShort()` → `"WTNB"` / `"Open"`
- `handle_waitlist_actions.ts:73-75` — `formatDivisionLabel()` → `"WTNB+"` / `"Open"` (private)
- `get_league_waitlist_selection.ts:9` — `formatDivisionLabel()` → identical duplicate

**Action:**
- [ ] Add `formatDivisionLabel()` to `utils/formatters.ts` (returning `"WTNB+"` / `"Open"`)
- [ ] Delete the 2 private duplicates
- [ ] Audit whether `formatDivisionShort` (which returns `"WTNB"` without the `+`) is still needed vs. using `formatDivisionLabel` everywhere

**Success:** One import for division formatting. Zero private division formatters.

---

### 1e: Consolidate base URL

**Problem:** Store base URL defined twice independently.

- `config.ts:12` — `BARS_URLS.website = "https://www.bigapplerecsports.com"`
- `utils/formatters.ts:3` — `const STORE_BASE = "https://www.bigapplerecsports.com"`

**Action:**
- [ ] Delete `STORE_BASE` from `formatters.ts`
- [ ] Import `BARS_URLS.website` from `config.ts` (or extract the domain to a single `ORG_DOMAIN` constant that both URL builders and email address formatters reference)

**Success:** One source of truth for the store URL.

---

## Stage 2: Type Cleanup

### 2a: `WaitlistEntry` should carry a `League`

**Problem:** `WaitlistEntry` stores `sport`, `day`, `division` as flat strings.
Every consumer reconstructs a `League` from them. The cast at `display.ts:88`
(`{ sport, day, division } as League`) is unsound — creates a `League` missing
`year` and `season`.

**Action:**
- [ ] Add `league: League` to `WaitlistEntry` (populated by `sheet_parser.ts` using `CURRENT_YEAR`/`CURRENT_SEASON`)
- [ ] Remove `sport`, `day`, `division` from `WaitlistEntry` (or keep as computed getters if backward compat is needed temporarily)
- [ ] Delete `entryLeague()` from `handle_waitlist_actions.ts`
- [ ] Fix the unsound cast at `display.ts:88` — use `entry.league` directly
- [ ] Update all consumers: `sheet_parser.ts`, `display.ts`, `handle_waitlist_actions.ts`, `resolve_waitlist_order.ts`

**Success:** No ad-hoc `League` reconstruction. The unsound `as League` cast is
gone.

---

### 2b: Extract shared `WaitlistAction` type

**Problem:** The shape `{ type, rowNumber, firstName, emailAddress, sport, day, division }`
is constructed in `handle_waitlist_actions.ts:337-347`, serialized to JSON,
parsed in `update_waitlist_spreadsheet.ts:49-54`, and also produced by
`resolve_waitlist_order.ts:61-67` — each with its own local interface.

**Action:**
- [ ] Create `lib/waitlists/action_types.ts` exporting `WaitlistAction`
- [ ] Import in all 3 files; delete the 3 local definitions

**Success:** One shared type for the workflow boundary. Drift caught at compile
time.

---

### 2c: Remove dead types from `waitlist_entry_types.ts`

**Problem:** Lines 42-82 define `WaitlistSignup`, `CrossLeagueInfo`,
`WaitlistSignupDisplay`, `ProcessWaitlistSignupsState` — imported nowhere.

**Action:**
- [ ] Delete lines 42-82 after Stage 2a lands (the `league: League` field on
  `WaitlistEntry` supersedes the aspirational `WaitlistSignup`)
- [ ] Or: if the aspirational types represent a better target shape, adopt them
  and delete the old types instead

**Success:** `waitlist_entry_types.ts` contains only types with active consumers.

---

### 2d: Move `ActionResult` out of `display.ts`

**Problem:** `ActionResult` (defined in `display.ts:11-28`) is a processing
concern — it tracks Shopify/email success/failure per row. It's constructed in
`handle_waitlist_actions.ts` and consumed by both `display.ts` formatting and
the submission orchestration. It doesn't belong in a display/formatting module.

**Action:**
- [ ] Move `ActionResult` to `lib/waitlists/action_types.ts` (alongside `WaitlistAction`)
- [ ] Re-export from `display.ts` if needed for backward compat during migration

**Success:** Processing types live with processing types. Display module is pure
formatting.

---

### 2e: Move `ModalState` to a shared location

**Problem:** `ModalState` is defined locally in `handle_waitlist_actions.ts:62-72`.
The unused `ProcessWaitlistSignupsState` in `waitlist_entry_types.ts` is a
better-typed version (`sel` is `Record<string, "admit" | "remove">` instead of
`Record<string, string>`).

**Action:**
- [ ] Move `ModalState` to `lib/waitlists/action_types.ts` with the stricter
  `sel` typing from `ProcessWaitlistSignupsState`
- [ ] Eliminate the `state as unknown as Record<string, unknown>` casts in the
  capture function calls (fix the capture functions to accept a generic state, or
  have `ModalState` extend a base interface they understand)

**Success:** Zero `as unknown as Record<string, unknown>` casts in the handler.

---

## Stage 3: Extract `formatStatusTimestamp` and `statusText`

**Problem:** `formatStatusTimestamp()` in `update_waitlist_spreadsheet.ts:9-18`
is a side-effecting function (`new Date()`) living in a Slack function definition
file. `statusText()` is a pure formatter also in that file. Both are imported by
`handle_waitlist_actions.ts`, creating a coupling where the handler imports from
a different function's definition file.

**Action:**
- [ ] Create `lib/waitlists/status_format.ts`:
  - `formatStatusTimestamp(now: Date = new Date()): string` — make the `Date`
    injectable for testability; defaults to `new Date()` for callers that don't care
  - `statusText(type: string, timestamp: string): string` — move as-is
- [ ] Update imports in `handle_waitlist_actions.ts` and `update_waitlist_spreadsheet.ts`
- [ ] `update_waitlist_spreadsheet.ts` becomes purely a Slack function definition
  (no exported utility functions)

**Success:** Function definition files define functions, not utilities. Timestamp
is injectable for testing.

---

## Stage 4: Decompose the Handler

The core refactor. After Stages 1-3, the handler's dependencies are clean; now
split its 658 lines into focused modules.

### 4a: Extract row processing — `lib/waitlists/row_processing.ts`

**Problem:** `buildRowProcessing()` (CC=21) and `executeRowProcessing()` mix
Shopify tag planning, email building, status text construction, and result
assembly in one monolith.

**Split into three focused builders + one orchestrator:**

- [ ] `planShopifyTag(shopify, entry, league): Promise<{ tagPlan, notes, customerAdminUrl? }>`
  — Shopify product lookup + customer tag planning. Pure Shopify concern.
- [ ] `planEmail(google, entry, league, shouldEmail): Promise<{ emailRequest, emailMessage, notes }>`
  — Email message construction + Gmail request building. Pure email concern.
- [ ] `buildRowResult(entry, type, league, tagPlan?, emailPlan?): ActionResult`
  — Assembles the `ActionResult` from the per-client plans. No I/O.
- [ ] Orchestrator remains `buildRowProcessing()` but becomes a thin caller of
  the three above (~15 lines, CC ≤ 3)

**Also extract execution by concern:**
- [ ] `executeShopifyTag(shopify, tagPlan, result): Promise<void>` — try/catch
  Shopify mutation, update `result.shopifyOk/shopifyError/customerAdminUrl`
- [ ] `executeSendNotification(emailRequest, result): Promise<void>` — try/catch
  email send, update `result.emailOk/emailError/emailed`
- [ ] `executeRowProcessing()` becomes: call `executeShopifyTag`, then
  conditionally call `executeSendNotification` (~10 lines)

**Success:** Each client concern (Shopify, email, sheet) is independently
testable and reusable by other workflows. `buildRowProcessing` CC drops from 21
to ≤ 3.

---

### 4b: Extract dry-run step conversion — `lib/waitlists/dry_run_steps.ts`

**Problem:** `toDryRunSteps()` and `htmlToText()` and `buildEmailCopy()` live in
the handler file but are pure data transforms.

**Action:**
- [ ] Move `toDryRunSteps()`, `htmlToText()`, `buildEmailCopy()` to
  `lib/waitlists/dry_run_steps.ts`
- [ ] Import from the handler

**Success:** Handler file loses ~55 lines. Dry-run rendering is testable in
isolation.

---

### 4c: Extract modal construction — `lib/waitlists/modal.ts`

**Problem:** `buildListView()` (lines 108-189) and supporting constants
(`SPORT_ABBR`, `isContacted()`) are 80+ lines of UI construction in the handler.

**Action:**
- [ ] Move `buildListView()`, `SPORT_ABBR`, `isContacted()`,
  `formatDivisionLabel` (after 1d, just the import) to `lib/waitlists/modal.ts`
- [ ] Handler imports `buildListView` from the new module

**Success:** Handler file drops another 80+ lines. Modal construction is testable
without the Slack function machinery.

---

### 4d: Slim the handler to a thin orchestrator

**After 4a-4c, `handle_waitlist_actions.ts` should contain only:**
1. `HandleWaitlistActionsFunction` definition (~20 lines)
2. Initial handler: fetch waitlists → open modal → `return { completed: false }` (~10 lines)
3. Block action handler: capture state → paginate → update modal (~15 lines)
4. Submission handler: capture state → build phase → dry-run branch → execute
   phase → post message → complete (~50 lines of orchestration, no domain logic)
5. Close handler: complete with empty actions (~10 lines)

**Target:** ~120 lines (down from 658). Every domain concern imported, not defined.

- [ ] Verify handler is purely wiring (Slack events → domain functions → Slack responses)
- [ ] No domain logic remains inline in any handler callback

**Success:** Handler reads as a routing table. Each callback is ≤ 20 lines.

---

## Stage 5: Merge Redundant Network Calls

### 5a: Fold `resolveStatusColumnIndex` into `fetchWaitlists`

**Problem:** `resolveStatusColumnIndex()` fetches `A1:Z1` separately. The header
row is already present in the `fetchWaitlists` response (`rows[0]`). Two network
calls where one suffices.

**Action:**
- [ ] Have `fetchWaitlists` (or `parseWaitlistRows`) return `statusColumnIndex`
  alongside the parsed leagues
- [ ] Add `statusColumnIndex: number` to `LeagueWaitlists`
- [ ] Delete `resolveStatusColumnIndex` export from `sheet_service.ts`
- [ ] Update `handle_waitlist_actions.ts` and `update_waitlist_spreadsheet.ts`

**Success:** One fewer HTTP call per submit. `resolveStatusColumnIndex` is gone.

---

## Stage 6: `config.ts` Decomposition (Future)

Low urgency but high readability gain. Not blocking the handler refactor.

**Problem:** 447 lines mixing season constants, URL builders, Slack UI config,
Gmail sender config, refund channel routing, Sheet IDs, and the full league data
registry.

**Suggested split:**
- [ ] `config/season.ts` — `CURRENT_YEAR`, `CURRENT_SEASON`, weekday ordering
- [ ] `config/urls.ts` — `BARS_URLS`, `productPageUrl`, `shopifyCustomerAdminUrl`
- [ ] `config/slack.ts` — `SLACK_LINK_TEXT`, `ACTION_OPTIONS`, `ENTRIES_PER_PAGE`, capture configs
- [ ] `config/gmail.ts` — `DEFAULT_GMAIL_SENDER`
- [ ] `config/refunds.ts` — `REFUND_TEST_CHANNEL`, `REFUND_REVIEW_CHANNEL`, `resolveRefundChannel`
- [ ] `config/sheets.ts` — `WAITLIST_SPREADSHEET_ID`, `REFUND_SPREADSHEET_ID`, tab configs
- [ ] `config/leagues.ts` — `LEAGUES` registry, `LeagueConfig` interface (→ move interface to `types/league.ts`)
- [ ] `config.ts` re-exports from all of the above for backward compat during migration

**Success:** Each config concern is independently navigable. `LeagueConfig` lives
with `League` in `types/`.

---

## Dependency Order

```
Stage 1 (cross-cutting)  ← independently shippable, no ordering between 1a-1e
    ↓
Stage 2 (types)           ← 2a depends on 1a (league key utils)
    ↓
Stage 3 (status format)   ← independent, can parallelize with Stage 2
    ↓
Stage 4 (handler decomp)  ← depends on Stages 1-3 being landed
    ↓
Stage 5 (network merge)   ← depends on Stage 4d (handler is slim enough to see the seam)
    ↓
Stage 6 (config split)    ← independent, low priority, do whenever
```

---

## Files Created / Modified

### New files
| File | Stage | Purpose |
|------|-------|---------|
| `utils/league_key.ts` | 1a | `toLeagueKey`, `parseLeagueKey`, `leagueFromKey` |
| `lib/slack/blocks.ts` | 1b | Shared Block Kit primitives |
| `utils/log.ts` | 1c | `makeLogger` factory |
| `lib/waitlists/action_types.ts` | 2b,2d,2e | `WaitlistAction`, `ActionResult`, `ModalState` |
| `lib/waitlists/status_format.ts` | 3 | `formatStatusTimestamp`, `statusText` |
| `lib/waitlists/row_processing.ts` | 4a | `planShopifyTag`, `planEmail`, `buildRowResult`, `buildRowProcessing`, `executeShopifyTag`, `executeSendNotification`, `executeRowProcessing` |
| `lib/waitlists/dry_run_steps.ts` | 4b | `toDryRunSteps`, `htmlToText`, `buildEmailCopy` |
| `lib/waitlists/modal.ts` | 4c | `buildListView`, `SPORT_ABBR`, `isContacted` |

### Modified files
| File | Stage | Change |
|------|-------|--------|
| `utils/formatters.ts` | 1d,1e | Add `formatDivisionLabel`, remove `STORE_BASE` |
| `lib/slack/list_modal.ts` | 1b | Import from `blocks.ts`, delete local definitions |
| `lib/slack/dry_run.ts` | 1b | Import from `blocks.ts`, delete local definitions |
| `lib/slack/refund_eval_blocks.ts` | 1b | Import from `blocks.ts`, delete local definitions |
| `lib/waitlists/handlers/waitlist_entry_types.ts` | 2a,2c | Add `league: League` to `WaitlistEntry`, delete dead types |
| `lib/waitlists/handlers/sheet_parser.ts` | 2a | Populate `league` on `WaitlistEntry` |
| `lib/waitlists/display.ts` | 2a,2d | Use `entry.league`, move `ActionResult` out |
| `lib/waitlists/sheet_service.ts` | 5a | Return `statusColumnIndex` from `fetchWaitlists` |
| `functions/update_waitlist_spreadsheet.ts` | 2b,3 | Delete local `WaitlistAction`, `formatStatusTimestamp`, `statusText` |
| `functions/handle_waitlist_actions.ts` | ALL | Slim to ~120-line orchestrator |
| `functions/resolve_waitlist_order.ts` | 1a,2b | Use `toLeagueKey`, shared `WaitlistAction` |
| `functions/get_league_waitlist_selection.ts` | 1d | Import `formatDivisionLabel` |

### Deleted code (no new files needed)
| What | Stage | Where |
|------|-------|-------|
| `toLeague()`, `entryLeague()` | 1a,2a | `handle_waitlist_actions.ts` |
| `formatDivisionLabel()` (2 copies) | 1d | `handle_waitlist_actions.ts`, `get_league_waitlist_selection.ts` |
| Local `section/heading/divider` | 1b | 4 files |
| 5+ hand-rolled `log` constants | 1c | 5 files |
| `STORE_BASE` | 1e | `utils/formatters.ts` |
| Dead types (40 lines) | 2c | `waitlist_entry_types.ts` |
| `RowProcessing` interface | 4a | `handle_waitlist_actions.ts` (absorbed into `row_processing.ts`) |
| `buildRowProcessing` (100 lines) | 4a | `handle_waitlist_actions.ts` |
| `executeRowProcessing` (50 lines) | 4a | `handle_waitlist_actions.ts` |
| `toDryRunSteps` + `htmlToText` + `buildEmailCopy` (55 lines) | 4b | `handle_waitlist_actions.ts` |
| `buildListView` + helpers (80 lines) | 4c | `handle_waitlist_actions.ts` |

---

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| `handle_waitlist_actions.ts` lines | 658 | ~120 |
| `buildRowProcessing` cognitive complexity | 21 | ≤ 3 |
| Duplicated `formatDivisionLabel` | 3 copies | 1 |
| Ad-hoc `leagueKey.split("\|")` | 7+ | 0 |
| Duplicated Block Kit primitives | 4 files | 1 |
| Unsound `as League` casts | 1 | 0 |
| Dead types | 40 lines | 0 |
| `as unknown as Record<string, unknown>` casts | 4 | 0 |
| Separate `resolveStatusColumnIndex` call | 1 extra HTTP | 0 |
