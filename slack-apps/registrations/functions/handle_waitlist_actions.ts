/** Workflow boundary for the waitlist admit/remove flow.
 *
 *  Thin handler. Every concern lives in `domain/waitlist/`:
 *    - modal view shape → `modal.ts`
 *    - planning / execution / dry-run preview → `row_planning.ts` /
 *      `row_execution.ts` / `dry_run_steps.ts`
 *    - sheet I/O + status format → `sheet.ts` / `status_format.ts`
 *    - data types + result + per-row display → `types.ts` / `action_result.ts`
 *      / `display.ts`
 *
 *  This file only does SDK wiring (DefineFunction + handler registrations) plus
 *  an orchestrator (`processSelections`) that sequences the domain calls. */

import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import type { SlackAPIClient } from "deno-slack-api/types.ts";

import {
    ACTION_PREFIX_CHECKBOX,
    ACTION_PREFIX_DROPDOWN,
    buildListView,
    CALLBACK_ID,
    ENTRIES_PER_PAGE,
    type ModalState,
    NO_ACTION_DROPDOWN_VALUES,
} from "../views/waitlist/list_modal.ts";
import { buildWaitlistConfirmModal } from "../views/waitlist/confirm_modal.ts";
import { buildWaitlistResultMessage } from "../views/waitlist/result_message.ts";

import { columnToLetter, getOrCreateGoogleClient } from "../shared/google/client.ts";
import {
    captureCheckboxSelections,
    captureDropdownSelections,
    extractModalState,
} from "../shared/slack/modal_state.ts";
import { postDryRunPreviews } from "../shared/slack/dry_run.ts";
import {
    completeWithEmpty,
    makeWorkflowCompleter,
    processorUserId,
} from "../shared/slack/workflow.ts";

import { createShopifyClient } from "../legacy/shopify_client/client.ts";

import { leagueFromKey } from "../domain/league/identity.ts";

import { buildRowProcessing } from "../domain/waitlist/row_planning.ts";
import { executeRowProcessing } from "../domain/waitlist/row_execution.ts";
import {
    formatDryRunHeader,
    formatRowLabel,
    toDryRunSteps,
} from "../views/waitlist/dry_run_steps.ts";
import { fetchWaitlists } from "../domain/waitlist/sheet.ts";
import { formatStatusTimestamp } from "../domain/waitlist/status_format.ts";
import type { LeagueWaitlists, WaitlistAction, WaitlistEntry } from "../domain/waitlist/types.ts";

// ────────────────────────────────────────────────────────────────────────────
// Constants
// ────────────────────────────────────────────────────────────────────────────

/** Pushed confirmation step; carries the captured state in its `private_metadata`. */
const CONFIRM_CALLBACK_ID = "confirm_waitlist_actions";

const log = (fn: string, ...args: unknown[]) => console.log(`[waitlist_actions:${fn}]`, ...args);

// TODO(surface-to-slack): warnings/errors here are only console.log/error'd, which
// lands in Slack's run logs — those are hard to find and often lack enough detail
// to debug. In a later stage, capture warnings/errors and post a concise diagnostic
// (trace, league, row, request label, error) back to the originating channel/thread
// so operators can self-diagnose without digging through platform logs.

// ────────────────────────────────────────────────────────────────────────────
// State capture (handler-specific glue around the generic shared/ helpers)
// ────────────────────────────────────────────────────────────────────────────

/** Read the persisted state out of `private_metadata` AND fold in the visible
 *  page's freshly-ticked dropdowns/checkboxes. Used by pagination and step-1
 *  submit — anywhere new input values may have appeared since the last capture. */
// deno-lint-ignore no-explicit-any
function captureModalStateWithInputs(body: any): ModalState {
    const state = extractModalState<ModalState>(body);
    state.sel = captureDropdownSelections(body, state.sel, {
        actionIdPrefix: ACTION_PREFIX_DROPDOWN,
        noneValues: NO_ACTION_DROPDOWN_VALUES,
    });
    state.email = captureCheckboxSelections(body, state.email, {
        actionIdPrefix: ACTION_PREFIX_CHECKBOX,
    });
    return state;
}

/** Selections that mean an actual action (vs "No Changes"). */
function actionableSelections(state: ModalState): [string, string][] {
    return Object.entries(state.sel ?? {}).filter(
        ([, type]) => type === "admit" || type === "remove",
    ) as [string, string][];
}

function buildRowIndex(waitlists: LeagueWaitlists): Map<number, WaitlistEntry> {
    return new Map(
        Object.values(waitlists.leagues)
            .flatMap((lw) => lw.entries)
            .map((e) => [e.rowNumber, e]),
    );
}

/** First+last name of the player at a captured sheet row (falls back to the
 *  row number when the row no longer resolves). Shared by every name-listing
 *  display the handler hands to a view builder. */
function resolveFullName(byRow: Map<number, WaitlistEntry>, rowStr: string): string {
    const e = byRow.get(Number(rowStr));
    return `${e?.firstName ?? ""} ${e?.lastName ?? ""}`.trim() || `Row ${rowStr}`;
}

// ────────────────────────────────────────────────────────────────────────────
// Orchestrator
// ────────────────────────────────────────────────────────────────────────────

/** Run the captured selections. Same path for dry-run (preview only) and real
 *  execution — the only branch is the dry/real split late in the function.
 *
 *  Exported for dry-run regression tests; the SDK view-submission handler is a
 *  one-liner around this. */
export async function processSelections(
    state: ModalState,
    // deno-lint-ignore no-explicit-any
    body: any,
    client: SlackAPIClient,
    env: Record<string, string>,
): Promise<void> {
    const complete = makeWorkflowCompleter(client, body);

    const selections = actionableSelections(state);
    if (selections.length === 0) {
        await complete("[]");
        return;
    }

    log("submit", { selections: selections.map(([row, type]) => `${type}:${row}`) });

    // Fresh fetch — selections reference sheet row numbers, so resolve against
    // current data. (Row resolution risk: if rows are inserted/deleted/reordered
    // in the sheet between modal open and Done, a captured row number can resolve
    // to a different person here. Future: key selections by stable identity.)
    const waitlists = await fetchWaitlists(env);
    const byRow = buildRowIndex(waitlists);

    // Build phase: produce the exact PreparedRequests for every row WITHOUT
    // sending them. Dry-run displays these; the real run executes them.
    const shopify = createShopifyClient(env);
    const google = getOrCreateGoogleClient(env);
    const fallbackLeague = leagueFromKey(state.league);
    // One clock read per run — every row's status text pins the same timestamp.
    const timestamp = formatStatusTimestamp(new Date());

    const processed = await Promise.all(
        selections.map(([rowStr, type]) =>
            buildRowProcessing({
                rowStr,
                type: type as "admit" | "remove",
                entry: byRow.get(Number(rowStr)),
                shouldEmail: state.email?.[rowStr] === true,
                shopify,
                google,
                fallbackLeague,
                timestamp,
                sheetUrl: waitlists.url,
            })
        ),
    );

    const outputActions: WaitlistAction[] = processed.map((p) => {
        const lg = p.result.league ?? fallbackLeague;
        return {
            type: p.result.type,
            rowNumber: String(p.result.rowNumber),
            firstName: p.result.firstName,
            lastName: p.entry?.lastName ?? "",
            emailAddress: p.result.email,
            sport: lg.sport,
            day: lg.day,
            division: lg.division,
        };
    });

    if (state.dry) {
        const statusCol = columnToLetter(waitlists.statusColumnIndex);
        await postDryRunPreviews(
            client,
            state.ch,
            processed.map((p) => ({
                header: formatDryRunHeader(p),
                label: formatRowLabel(p),
                steps: toDryRunSteps(p, statusCol),
            })),
            (preview, error) => log("dry_run.post_failed", { label: preview.label, error }),
        );
        await complete(JSON.stringify(outputActions));
        return;
    }

    for (const p of processed) await executeRowProcessing(shopify, p);

    const remaining = (waitlists.leagues[state.league]?.total ?? selections.length) -
        processed.length;
    const { text, blocks } = buildWaitlistResultMessage({
        results: processed.map((p) => p.result),
        processedBy: processorUserId(body),
        remaining,
        sheetUrl: waitlists.url,
    });
    await client.chat.postMessage({ channel: state.ch, text, blocks });

    // The Status column write happens in the next workflow step
    // (UpdateWaitlistSpreadsheet), which consumes this actions_json output.
    await complete(JSON.stringify(outputActions));
}

// ────────────────────────────────────────────────────────────────────────────
// SlackFunction definition & handler wiring
// ────────────────────────────────────────────────────────────────────────────

export const HandleWaitlistActionsFunction = DefineFunction({
    callback_id: CALLBACK_ID,
    title: "Selecting Player(s) to process",
    source_file: "functions/handle_waitlist_actions.ts",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            channel_id: { type: Schema.slack.types.channel_id },
            selected_league: { type: Schema.types.string },
            dry_run: { type: Schema.types.boolean },
        },
        required: ["interactivity", "channel_id", "selected_league"],
    },
    output_parameters: {
        properties: {
            actions_json: { type: Schema.types.string },
        },
        required: ["actions_json"],
    },
});

const handler = SlackFunction(HandleWaitlistActionsFunction, async ({ inputs, client, env }) => {
    const state: ModalState = {
        ch: inputs.channel_id,
        league: inputs.selected_league,
        off: 0,
        sel: {},
        dry: inputs.dry_run === true,
    };
    const waitlists = await fetchWaitlists(env);

    const openRes = await client.views.open({
        interactivity_pointer: inputs.interactivity.interactivity_pointer,
        view: buildListView(waitlists, state),
    });
    if (!openRes.ok) return { error: `Failed to open modal: ${openRes.error}` };
    return { completed: false };
});

handler.addBlockActionsHandler(/^(next|prev)_page$/, async ({ action, body, client, env }) => {
    const state = captureModalStateWithInputs(body);
    state.off = action.action_id === "next_page"
        ? (state.off ?? 0) + ENTRIES_PER_PAGE
        : Math.max(0, (state.off ?? 0) - ENTRIES_PER_PAGE);

    const waitlists = await fetchWaitlists(env);
    await client.views.update({
        view_id: body.view?.id,
        view: buildListView(waitlists, state),
    });
});

// Email checkboxes only carry state that's read on pagination/submit. Toggling
// one fires a block action with no view change, so just ack it (no-op).
handler.addBlockActionsHandler(/^email_r/, () => {});

/** Step 1 submit: capture selections, then push a confirmation step. The reviewer
 *  can edit (native back chevron), Cancel (handled by the list view's close
 *  handler), or Confirm to run. No selections → complete the step cleanly. The
 *  full captured state rides in the confirm modal's `private_metadata`. */
handler.addViewSubmissionHandler(CALLBACK_ID, async ({ body, client, env }) => {
    const state = captureModalStateWithInputs(body);
    const selections = actionableSelections(state);
    if (selections.length === 0) {
        await completeWithEmpty(client, body);
        return;
    }

    const waitlists = await fetchWaitlists(env);
    const byRow = buildRowIndex(waitlists);

    return {
        response_action: "push",
        view: buildWaitlistConfirmModal({
            callbackId: CONFIRM_CALLBACK_ID,
            admitNames: selections.filter(([, t]) => t === "admit")
                .map(([r]) => resolveFullName(byRow, r)),
            removeNames: selections.filter(([, t]) => t === "remove")
                .map(([r]) => resolveFullName(byRow, r)),
            dry: state.dry === true,
            metadata: JSON.stringify(state),
        }),
    };
});

// Step 2 submit (confirmation): run the captured selections. The confirm modal
// has no inputs, so we read state straight from `private_metadata`.
handler.addViewSubmissionHandler(CONFIRM_CALLBACK_ID, async ({ body, client, env }) => {
    const state = extractModalState<ModalState>(body);
    await processSelections(state, body, client, env);
});

// Closing the modal (Cancel/Close, incl. the empty-waitlist view which has no
// submit) must still complete the workflow step — otherwise the run hangs.
handler.addViewClosedHandler(CALLBACK_ID, async ({ body, client }) => {
    await completeWithEmpty(client, body);
});

export default handler;
