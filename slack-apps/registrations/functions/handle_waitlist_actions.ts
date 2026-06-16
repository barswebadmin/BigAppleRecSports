import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { buildListModal } from "../lib/slack/list_modal.ts";
import {
    captureCheckboxSelections,
    captureDropdownSelections,
    extractModalState,
} from "../lib/slack/state.ts";
import {
    ACTION_OPTIONS,
    CHECKBOX_CAPTURE_CONFIG,
    CURRENT_SEASON,
    CURRENT_YEAR,
    DROPDOWN_CAPTURE_CONFIG,
    ENTRIES_PER_PAGE,
    productPageUrl,
    shopifyCustomerAdminUrl,
} from "../config.ts";
import { capitalize, formatDivisionLabel, formatProductHandle } from "../utils/formatters.ts";
import { columnToLetter, getOrCreateGoogleClient } from "../lib/clients/google/client.ts";
import { buildSendEmailRequest, executeSendEmail } from "../lib/clients/google/gmail.ts";
import type { EmailMessage } from "../lib/clients/google/types/email_message.ts";
import {
    fetchWaitlists,
    resolveStatusColumnIndex,
    WAITLIST_TAB,
} from "../lib/waitlists/sheet_service.ts";
import { ContactedStatuses } from "../lib/waitlists/handlers/waitlist_entry_types.ts";
import type {
    LeagueWaitlists,
    WaitlistEntry,
} from "../lib/waitlists/handlers/waitlist_entry_types.ts";
import type { WaitlistAction } from "../lib/waitlists/waitlist_action.ts";
import { buildWaitlistAdmitEmail } from "../lib/waitlists/admit_email.ts";
import {
    type ActionResult,
    buildWaitlistConfirmModal,
    buildWaitlistResultMessage,
    formatEntryContextLines,
    formatEntryTitle,
    formatReadOnlyEntry,
} from "../lib/waitlists/display.ts";
import type { SlackAPIClient } from "deno-slack-api/types.ts";
import { createShopifyClient } from "../lib/clients/shopify/client.ts";
import {
    type CustomerTagPlan,
    executeCustomerTag,
    planCustomerTag,
} from "../lib/clients/shopify/customer_ops.ts";
import { findProductByHandle } from "../lib/clients/shopify/product_ops.ts";
import type { PreparedRequest } from "../lib/clients/prepared_request.ts";
import { type DryRunStep, postDryRunPreviews } from "../lib/slack/dry_run.ts";
import { formatStatusTimestamp, statusText } from "./update_waitlist_spreadsheet.ts";
import type { League } from "../types/league.ts";
import { leagueFromKey, parseLeagueKey } from "../lib/waitlists/league_key.ts";

const CALLBACK_ID = "handle_waitlist_actions";
/** Pushed confirmation step; carries the captured state in its private_metadata. */
const CONFIRM_CALLBACK_ID = "confirm_waitlist_actions";

const log = (fn: string, ...args: unknown[]) => console.log(`[waitlist_actions:${fn}]`, ...args);

// TODO(surface-to-slack): warnings/errors here are only console.log/error'd, which
// lands in Slack's run logs — those are hard to find and often lack enough detail
// to debug. In a later stage, capture warnings/errors and post a concise diagnostic
// (trace, league, row, request label, error) back to the originating channel/thread
// so operators can self-diagnose without digging through platform logs.

interface ModalState {
    ch: string;
    league: string;
    off?: number;
    sel?: Record<string, string>;
    /** Row id → true when the reviewer ticked "email this player". Default: no email. */
    email?: Record<string, boolean>;
    /** Dry-run mode: build + display the exact requests, execute nothing. */
    dry?: boolean;
}

/** 2-letter sport codes for the space-constrained (24-char) modal title. */
const SPORT_ABBR: Record<string, string> = {
    kickball: "KB",
    pickleball: "PB",
    dodgeball: "DB",
    bowling: "BL",
};

function isContacted(entry: WaitlistEntry): boolean {
    if (!entry.status) return false;
    const norm = entry.status.toLowerCase();
    return ContactedStatuses.some((k) => norm.includes(k));
}

/** League for a sheet entry: year/season from config, sport/day/division from the sheet. */
function entryLeague(entry: WaitlistEntry): League {
    return {
        year: CURRENT_YEAR,
        season: CURRENT_SEASON,
        sport: entry.sport,
        day: entry.day,
        division: entry.division,
    };
}

function buildListView(waitlists: LeagueWaitlists, state: ModalState): Record<string, unknown> {
    const league = waitlists.leagues[state.league];
    const entries = league?.entries ?? [];
    const total = league?.total ?? 0;
    const { sport, day, division: div } = parseLeagueKey(state.league);
    const dayLabel = capitalize(day);
    const sportLabel = capitalize(sport);
    const divLabel = formatDivisionLabel(div);

    // Slack caps modal titles at 24 chars, so the title abbreviates everything:
    // "Waitlist for {Day3} {SPORT2} {Open|WTNB}". The "+" is dropped from WTNB+
    // because it would push the longest combos to 25 chars. The full, unabbreviated
    // "Waitlist for {Day} {Sport} ({Division})" lives in the sub-line below.
    const day3 = capitalize(day.slice(0, 3));
    const sportAbbr = SPORT_ABBR[sport] ?? capitalize(sport).slice(0, 2);
    const divTitle = div === "wtnb" ? "WTNB" : "Open";
    const title = `Waitlist for ${day3} ${sportAbbr} ${divTitle}`;

    if (entries.length === 0) {
        return buildListModal<WaitlistEntry>({
            callbackId: CALLBACK_ID,
            title,
            closeLabel: "Close",
            items: [],
            offset: 0,
            pageSize: ENTRIES_PER_PAGE,
            formatItemTitle: () => "",
            getItemId: (e) => e.rowNumber,
            getBlockId: (e) => `entry_r${e.rowNumber}`,
            getActionId: (e) => `action_r${e.rowNumber}`,
            actionOptions: ACTION_OPTIONS,
            paginationActionIds: { prev: "prev_page", next: "next_page" },
            metadata: JSON.stringify(state),
            emptyMessage:
                `Waitlist for *${dayLabel} ${sportLabel}* is detected to be empty. If you believe this is incorrect, please reach out to the web team.`,
        });
    }

    // Count stands out as a big-bold header; full league + division (which can't
    // fit the 24-char title) sits in the smaller sub-line.
    const headerText = `${total} ${total === 1 ? "person" : "people"} on the waitlist`;
    const subText = `${
        state.dry ? "DRY RUN ONLY — " : ""
    }Waitlist for ${dayLabel} ${sportLabel} (${divLabel})`;

    const instruction =
        "Select *Admit* to let people off the waitlist, or *Remove* if they are no longer waiting (update any selection to *No Changes* if it was accidental). Their Shopify profile(s) will be updated (or created) with a tag that unlocks the reg page as long as they're logged in. Click *Back*/*Next* at the bottom of the window to go backwards/forwards and see more waitlist entries.";

    return buildListModal<WaitlistEntry>({
        callbackId: CALLBACK_ID,
        title,
        submitLabel: "Submit",
        closeLabel: "Cancel",
        headerText,
        subText,
        instructionText: instruction,
        items: entries,
        offset: state.off ?? 0,
        pageSize: ENTRIES_PER_PAGE,
        formatItemTitle: (e) => formatEntryTitle(e),
        formatItemContextLines: (e) => formatEntryContextLines(e, state.league, waitlists.byEmail),
        getItemId: (e) => e.rowNumber,
        getBlockId: (e) => `entry_r${e.rowNumber}`,
        getActionId: (e) => `action_r${e.rowNumber}`,
        actionOptions: ACTION_OPTIONS,
        paginationActionIds: { prev: "prev_page", next: "next_page" },
        existingSelections: state.sel,
        checkbox: {
            getBlockId: (e) => `email_block_r${e.rowNumber}`,
            getActionId: (e) => `email_r${e.rowNumber}`,
            getOption: (e) => ({
                label: `Notify via email (${e.emailAddress})`,
                value: "email",
            }),
            existingSelections: state.email,
        },
        metadata: JSON.stringify(state),
        emptyMessage: "",
        shouldShowDropdown: (e) => !isContacted(e),
        formatReadOnlyLabel: (e) => formatReadOnlyEntry(e, state.league, waitlists.byEmail),
    });
}

export const HandleWaitlistActionsFunction = DefineFunction({
    callback_id: "handle_waitlist_actions",
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
    const state = extractModalState<ModalState>(body);
    captureDropdownSelections(
        body,
        state as unknown as Record<string, unknown>,
        "sel",
        DROPDOWN_CAPTURE_CONFIG,
    );
    captureCheckboxSelections(
        body,
        state as unknown as Record<string, unknown>,
        "email",
        CHECKBOX_CAPTURE_CONFIG,
    );
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

// Selection options that mean an actual action (vs "No Changes").
function actionableSelections(state: ModalState): [string, string][] {
    return Object.entries(state.sel ?? {}).filter(
        ([, type]) => type === "admit" || type === "remove",
    ) as [string, string][];
}

// deno-lint-ignore no-explicit-any
function executionId(body: any): string | undefined {
    return body.function_data?.execution_id;
}

// Step 1 submit: capture selections, then push a confirmation step. The reviewer
// can edit (native back chevron), Cancel (handled by the list view's close
// handler), or Confirm to run. No selections → nothing to confirm; complete the
// step cleanly. The full captured state rides in the confirm modal's
// private_metadata so the confirm handler reads it without any dropdowns.
handler.addViewSubmissionHandler(CALLBACK_ID, async ({ body, client, env }) => {
    const state = extractModalState<ModalState>(body);
    captureDropdownSelections(
        body,
        state as unknown as Record<string, unknown>,
        "sel",
        DROPDOWN_CAPTURE_CONFIG,
    );
    captureCheckboxSelections(
        body,
        state as unknown as Record<string, unknown>,
        "email",
        CHECKBOX_CAPTURE_CONFIG,
    );

    const selections = actionableSelections(state);
    if (selections.length === 0) {
        const execId = executionId(body);
        if (execId) {
            await client.functions.completeSuccess({
                function_execution_id: execId,
                outputs: { actions_json: "[]" },
            });
        }
        return;
    }

    // Resolve first/last names (only) for the confirmation modal.
    const waitlists = await fetchWaitlists(env);
    const byRow = new Map<number, WaitlistEntry>();
    for (const lw of Object.values(waitlists.leagues)) {
        for (const e of lw.entries) byRow.set(e.rowNumber, e);
    }
    const fullName = (rowStr: string) => {
        const e = byRow.get(Number(rowStr));
        return `${e?.firstName ?? ""} ${e?.lastName ?? ""}`.trim() || `Row ${rowStr}`;
    };

    return {
        response_action: "push",
        view: buildWaitlistConfirmModal({
            callbackId: CONFIRM_CALLBACK_ID,
            admitNames: selections.filter(([, t]) => t === "admit").map(([r]) => fullName(r)),
            removeNames: selections.filter(([, t]) => t === "remove").map(([r]) => fullName(r)),
            dry: state.dry === true,
            metadata: JSON.stringify(state),
        }),
    };
});

// Step 2 submit (confirmation): run the captured selections. Same path for
// dry-run (preview) and real execution — the only branch is inside.
handler.addViewSubmissionHandler(CONFIRM_CALLBACK_ID, async ({ body, client, env }) => {
    const state = extractModalState<ModalState>(body);
    await processSelections(state, body, client, env);
});

// Exported for Stage 8 dry-run regression tests — drives the confirm-submit path
// in-process without SDK modal wiring.
export async function processSelections(
    state: ModalState,
    // deno-lint-ignore no-explicit-any
    body: any,
    client: SlackAPIClient,
    env: Record<string, string>,
): Promise<void> {
    const execId = executionId(body);
    const complete = (actionsJson: string) =>
        execId
            ? client.functions.completeSuccess({
                function_execution_id: execId,
                outputs: { actions_json: actionsJson },
            })
            : Promise.resolve();

    const selections = actionableSelections(state);
    if (selections.length === 0) {
        await complete("[]");
        return;
    }

    log("submit", { selections: selections.map(([row, type]) => `${type}:${row}`) });

    const { sport, day, division } = parseLeagueKey(state.league);
    const league = leagueFromKey(state.league);

    // Fresh fetch: selections reference sheet row numbers, so resolve against current data.
    //
    // TODO(row-resolution-risk): selections are keyed by sheet row number, which is
    // only stable while the sheet is unchanged between opening the modal and clicking
    // Done. If rows are inserted/deleted/reordered in the sheet during that window, a
    // captured row number can resolve to a *different* person here. Revisit: key
    // selections by a stable identity (email or a row GUID) and reconcile against the
    // fresh fetch before acting.
    const waitlists = await fetchWaitlists(env);
    const byRow = new Map<number, WaitlistEntry>();
    for (const lw of Object.values(waitlists.leagues)) {
        for (const e of lw.entries) byRow.set(e.rowNumber, e);
    }

    const shopify = createShopifyClient(env);
    const google = getOrCreateGoogleClient(env);
    const timestamp = formatStatusTimestamp();

    // ── Build phase ──────────────────────────────────────────────────────
    // Produce the exact PreparedRequests for every row WITHOUT sending them.
    // Dry-run displays these; the real run executes them. Builders perform only
    // read/auth lookups (product-by-handle, customer search, token) needed to make
    // the bytes exact.
    const processed: RowProcessing[] = await Promise.all(
        selections.map(([rowStr, type]) =>
            buildRowProcessing({
                rowStr,
                type: type as "admit" | "remove",
                entry: byRow.get(Number(rowStr)),
                shouldEmail: state.email?.[rowStr] === true,
                shopify,
                google,
                fallbackLeague: league,
                timestamp,
                sheetUrl: waitlists.url,
            })
        ),
    );

    const outputActions: WaitlistAction[] = processed.map((p) => ({
        type: p.result.type,
        rowNumber: String(p.result.rowNumber),
        firstName: p.result.firstName,
        lastName: p.entry?.lastName ?? "",
        emailAddress: p.result.email,
        sport,
        day,
        division,
    }));

    // Locate the Status column by name once; the same index drives the dry-run
    // preview (e.g. Status → F10) and the real run's per-cell deep links.
    const statusColIdx = await resolveStatusColumnIndex(env);
    // deno-lint-ignore no-explicit-any
    const processedBy = (body as any).user?.id as string | undefined;

    if (state.dry) {
        const statusCol = columnToLetter(statusColIdx);
        await postDryRunPreviews(
            client,
            state.ch,
            processed.map((p) => ({
                header: `:test_tube: *DRY RUN* — would *${
                    p.type === "admit" ? "Admit" : "Remove"
                }* ${p.result.name} (${p.result.email || "no email"}) · email box: ${
                    p.shouldEmail ? "ON" : "off"
                }`,
                label: `${p.result.name} (${p.result.email || "no email"})`,
                steps: toDryRunSteps(p, statusCol),
            })),
            (preview, error) => log("dry_run.post_failed", { label: preview.label, error }),
        );
        // No sheet step downstream in dry-run; nothing is written.
        await complete(JSON.stringify(outputActions));
        return;
    }

    // ── Execute phase (real run) ─────────────────────────────────────────
    for (const p of processed) await executeRowProcessing(shopify, p);

    // One consolidated message for the whole run (single league at a time): the
    // league/processor/sheet link + remaining count once, each player a bullet.
    const remaining = (waitlists.leagues[state.league]?.total ?? selections.length) -
        processed.length;
    const { text, blocks } = buildWaitlistResultMessage(
        processed.map((p) => p.result),
        { processedBy, remaining, sheetUrl: waitlists.url },
    );
    await client.chat.postMessage({ channel: state.ch, text, blocks });

    // The Status column write happens in the next workflow step
    // (UpdateWaitlistSpreadsheet), which consumes this actions_json output.
    await complete(JSON.stringify(outputActions));
}

interface RowProcessing {
    rowStr: string;
    type: "admit" | "remove";
    entry?: WaitlistEntry;
    shouldEmail: boolean;
    result: ActionResult;
    tagPlan: CustomerTagPlan | null;
    emailRequest: PreparedRequest | null;
    emailMessage: EmailMessage | null;
    notes: string[];
    /** Dry-run sheet preview: the row write the downstream step would perform. */
    sheetUrl: string;
    insertedStatus: string;
}

// Exported for Stage 8 — builder seam when full handler invocation is awkward.
export async function buildRowProcessing(args: {
    rowStr: string;
    type: "admit" | "remove";
    entry?: WaitlistEntry;
    shouldEmail: boolean;
    shopify: ReturnType<typeof createShopifyClient>;
    google: ReturnType<typeof getOrCreateGoogleClient>;
    /** Used for display only when the row can't be resolved to a sheet entry. */
    fallbackLeague: League;
    timestamp: string;
    sheetUrl: string;
}): Promise<RowProcessing> {
    const { rowStr, type, entry, shouldEmail, shopify, google, fallbackLeague } = args;
    const rowNumber = Number(rowStr);
    // Year/season come from config; sport/day/division come from the sheet entry.
    const league: League = entry ? entryLeague(entry) : fallbackLeague;
    const result: ActionResult = {
        rowNumber,
        type,
        name: `${entry?.firstName ?? ""} ${entry?.lastName ?? ""}`.trim() || `row ${rowNumber}`,
        firstName: entry?.firstName ?? "",
        email: entry?.emailAddress ?? "",
        phone: entry?.phoneNumber,
        league,
        shopifyOk: true,
        emailOk: true,
        emailed: false,
        productUrl: productPageUrl(formatProductHandle(league)),
    };

    const notes: string[] = [];
    let tagPlan: CustomerTagPlan | null = null;
    let emailRequest: PreparedRequest | null = null;
    let emailMessage: EmailMessage | null = null;

    if (entry && type === "admit") {
        // Look the product up by its (config+sheet-derived) handle to anchor the tag
        // to a real product and surface season/config drift as a clear mismatch.
        const expectedHandle = formatProductHandle(league);
        const product = await findProductByHandle(shopify, expectedHandle);

        if (!product) {
            notes.push(
                `:warning: Shopify: no product found for handle \`${expectedHandle}\` — check season/year config. No tag will be applied.`,
            );
        } else {
            const waitlistTag = `${product.handle}-waitlist`;
            tagPlan = await planCustomerTag(shopify, entry.emailAddress, waitlistTag, {
                firstName: entry.firstName ?? "",
                lastName: entry.lastName ?? "",
                ...(entry.phoneNumber ? { phone: entry.phoneNumber } : {}),
            });
            if (tagPlan.existing?.id) {
                result.customerAdminUrl = shopifyCustomerAdminUrl(tagPlan.existing.id);
            }
            if (tagPlan.action === "noop") {
                notes.push(
                    `Shopify: customer already has \`${waitlistTag}\` — no mutation needed.`,
                );
            } else if (tagPlan.action === "update") {
                notes.push(
                    `Shopify: update existing customer \`${tagPlan.existing?.id}\` → tags become [${
                        tagPlan.finalTags.join(", ")
                    }].`,
                );
            } else {
                notes.push(
                    `Shopify: no customer for ${entry.emailAddress} → create with tag \`${waitlistTag}\`.`,
                );
            }
        }

        if (shouldEmail && entry.emailAddress) {
            emailMessage = buildWaitlistAdmitEmail(
                { firstName: entry.firstName, emailAddress: entry.emailAddress },
                league,
            );
            emailRequest = await buildSendEmailRequest(google, emailMessage);
        } else if (!shouldEmail) {
            notes.push("Email: box unticked → no email will be sent (tag only).");
        }
    }

    return {
        rowStr,
        type,
        entry,
        shouldEmail,
        result,
        tagPlan,
        emailRequest,
        emailMessage,
        notes,
        sheetUrl: args.sheetUrl,
        insertedStatus: statusText(type, args.timestamp),
    };
}

/** Render the HTML email body parts as readable plain text for dry-run display. */
function htmlToText(html: string): string {
    return html
        .replace(/<a\s+href="([^"]*)"[^>]*>(.*?)<\/a>/gi, "$2 ($1)")
        .replace(/<\/?(b|strong|i|em)>/gi, "")
        .replace(/<br\s*\/?>/gi, "\n")
        .replace(/&gt;/g, ">")
        .replace(/&lt;/g, "<")
        .replace(/&amp;/g, "&");
}

function buildEmailCopy(m: EmailMessage): string {
    return m.htmlBodyParts.map(htmlToText).join("\n\n");
}

// Exported for Stage 8 — dry-run preview seam.
export function toDryRunSteps(p: RowProcessing, statusCol: string): DryRunStep[] {
    const steps: DryRunStep[] = [];
    if (p.type === "admit") {
        // Shopify customer create/update (or a note for no-op / no tag resolved).
        const req = p.tagPlan?.request;
        if (req) {
            steps.push({
                kind: "shopify_customer",
                previousTags: p.tagPlan?.existing?.tags ?? [],
                request: { method: req.method, url: req.url, headers: req.headers },
                body: req.body,
            });
        } else {
            steps.push({
                kind: "shopify_customer",
                previousTags: p.tagPlan?.existing?.tags ?? [],
                request: null,
                note: p.notes[0],
            });
        }

        // Email send (or the skip note when the box was unticked).
        if (p.emailRequest && p.emailMessage) {
            const m = p.emailMessage;
            steps.push({
                kind: "email",
                request: {
                    method: p.emailRequest.method,
                    url: p.emailRequest.url,
                    headers: p.emailRequest.headers,
                },
                to: m.to,
                senderEmail: m.sendAs.emailAddress,
                subject: m.subject,
                replyTo: m.replyTo,
                cc: m.cc,
                copy: buildEmailCopy(m),
            });
        } else {
            const skip = p.notes.find((n) => n.startsWith("Email"));
            if (skip) steps.push({ kind: "note", title: "Send email notification", note: skip });
        }
    }

    // Sheet write the downstream step would perform (admit + remove).
    steps.push({
        kind: "sheet",
        sheetUrl: p.sheetUrl,
        tabName: WAITLIST_TAB.name,
        rowNumber: p.result.rowNumber,
        columnName: `Status (${statusCol}${p.result.rowNumber})`,
        existingValue: p.entry?.status?.trim() || "(empty)",
        insertedValue: p.insertedStatus,
    });
    return steps;
}

async function executeRowProcessing(
    shopify: ReturnType<typeof createShopifyClient>,
    p: RowProcessing,
): Promise<void> {
    if (p.type !== "admit" || !p.entry) return;

    // TODO(shopify-error-differentiation): today every Shopify failure is treated
    // as a per-row failure (surfaced individually; other rows still run).
    // Differentiate by classification (see ShopifyClient.gqlClassified):
    //   - Client/transport-level failures that recur for every row in this
    //     execution — BAD_REQUEST (malformed input) or FORBIDDEN (bad auth/token)
    //     — should ABORT the remaining admit→email steps when >1 person is being
    //     processed, and report *why* (bad request vs. bad auth) once.
    //   - Failures specific to a single row (e.g. customerCreate userErrors) should
    //     NOT abort the batch; keep going and surface each one in the Slack summary.
    if (p.tagPlan) {
        try {
            const res = await executeCustomerTag(shopify, p.tagPlan);
            if (!res.ok) {
                p.result.shopifyOk = false;
                p.result.shopifyError = res.error;
            } else if (res.customer?.id) {
                p.result.customerAdminUrl = shopifyCustomerAdminUrl(res.customer.id);
            }
        } catch (e) {
            p.result.shopifyOk = false;
            p.result.shopifyError = e instanceof Error ? e.message : String(e);
            console.error(`[shopify:${p.result.rowNumber}]`, e);
        }
    }

    // Email only when the box was ticked (emailRequest exists) AND the Shopify tag
    // succeeded — the login link is useless without the tag.
    if (p.emailRequest && p.result.shopifyOk) {
        try {
            const emailRes = await executeSendEmail(p.emailRequest);
            if (!emailRes.ok) {
                p.result.emailOk = false;
                p.result.emailError = emailRes.error;
            } else {
                p.result.emailed = true;
            }
        } catch (e) {
            p.result.emailOk = false;
            p.result.emailError = e instanceof Error ? e.message : String(e);
            console.error(`[email:${p.result.rowNumber}]`, e);
        }
    }
}

// Closing the modal (Cancel/Close, incl. the empty-waitlist view which has no
// submit) must still complete the workflow step — otherwise the run hangs.
handler.addViewClosedHandler(CALLBACK_ID, async ({ body, client }) => {
    // deno-lint-ignore no-explicit-any
    const execId = (body as any).function_data?.execution_id;
    if (execId) {
        await client.functions.completeSuccess({
            function_execution_id: execId,
            outputs: { actions_json: "[]" },
        });
    }
});

export default handler;
