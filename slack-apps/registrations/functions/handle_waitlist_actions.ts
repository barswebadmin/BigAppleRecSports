import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { buildListModal, type RichTextElement } from "../lib/slack/list_modal.ts";
import { captureDropdownSelections, extractModalState } from "../lib/slack/state.ts";
import { buildActionMessage } from "../lib/slack/messages.ts";
import {
    ACTION_OPTIONS,
    CURRENT_SEASON,
    CURRENT_YEAR,
    DROPDOWN_CAPTURE_CONFIG,
    ENTRIES_PER_PAGE,
    getLeague,
    GOOGLE_SHEETS,
} from "../config.ts";
import { capitalize } from "../utils/formatters.ts";
import { getOrCreateGoogleClient } from "../lib/clients/google/client.ts";
import { sendEmail } from "../lib/clients/google/gmail.ts";
import { parseWaitlistRows } from "../lib/waitlists/handlers/sheet_parser.ts";
import { ContactedStatuses } from "../lib/waitlists/handlers/waitlist_entry_types.ts";
import type {
    LeagueWaitlists,
    WaitlistEntry,
} from "../lib/waitlists/handlers/waitlist_entry_types.ts";
import { buildWaitlistAdmitEmail } from "../lib/waitlists/admit_email.ts";
import {
    type ActionResult,
    formatActionResult,
    formatEntryLabel,
} from "../lib/waitlists/display.ts";
import { createShopifyClient } from "../lib/clients/shopify/client.ts";
import { findOrCreateCustomerWithTag } from "../lib/clients/shopify/customer_ops.ts";
import { getProductHandle } from "../lib/clients/shopify/product_ops.ts";
import type { League } from "../types/league.ts";

const CALLBACK_ID = "handle_waitlist_actions";
const SHEET = GOOGLE_SHEETS.waitlists;
const TAB = { name: SHEET.tab_name, id: SHEET.tab_id };

const log = (fn: string, ...args: unknown[]) => console.log(`[waitlist_actions:${fn}]`, ...args);

interface ModalState {
    ch: string;
    league: string;
    off?: number;
    sel?: Record<string, string>;
}

function formatDivisionLabel(div: string): string {
    return div === "wtnb" ? "WTNB+" : "Open";
}

function formatLeagueLabel(leagueKey: string): string {
    const [sport, day, div] = leagueKey.split("|");
    return `${capitalize(sport)} - ${capitalize(day)} - ${formatDivisionLabel(div)} Division`;
}

function isContacted(entry: WaitlistEntry): boolean {
    if (!entry.status) return false;
    const norm = entry.status.toLowerCase();
    return ContactedStatuses.some((k) => norm.includes(k));
}

function toLeague(leagueKey: string): League {
    const [sport, day, division] = leagueKey.split("|");
    return { year: CURRENT_YEAR, season: CURRENT_SEASON, sport, day, division };
}

async function fetchWaitlists(env: Record<string, string>): Promise<LeagueWaitlists> {
    const google = getOrCreateGoogleClient(env);
    const { url, values } = await google.getSpreadsheet(SHEET.spreadsheet_id, TAB, "A1:J");
    return parseWaitlistRows(values, url);
}

function buildListView(waitlists: LeagueWaitlists, state: ModalState): Record<string, unknown> {
    const league = waitlists.leagues[state.league];
    const entries = league?.entries ?? [];
    const total = league?.total ?? 0;
    const leagueLabel = formatLeagueLabel(state.league);

    return buildListModal<WaitlistEntry>({
        callbackId: CALLBACK_ID,
        title: "Waitlist",
        submitLabel: "Done",
        headerText: leagueLabel,
        summaryElements: [
            { text: `${total} people`, style: { bold: true } },
            { text: " currently on the waitlist." },
        ] as RichTextElement[],
        instructionText: "Select *Admit* or *Remove* for one or more people, then click *Done*.",
        items: entries,
        offset: state.off ?? 0,
        pageSize: ENTRIES_PER_PAGE,
        formatItemLabel: (e) => formatEntryLabel(e, state.league, waitlists.byEmail),
        getItemId: (e) => e.rowNumber,
        getBlockId: (e) => `entry_r${e.rowNumber}`,
        getActionId: (e) => `action_r${e.rowNumber}`,
        actionOptions: ACTION_OPTIONS,
        paginationActionIds: { prev: "prev_page", next: "next_page" },
        existingSelections: state.sel,
        metadata: JSON.stringify(state),
        emptyMessage: `No active entries for *${leagueLabel}*`,
        shouldShowDropdown: (e) => !isContacted(e),
        formatReadOnlyLabel: (e) =>
            `${
                formatEntryLabel(e, state.league, waitlists.byEmail)
            }\n:white_check_mark: _${e.status}_`,
    });
}

export const HandleWaitlistActionsFunction = DefineFunction({
    callback_id: "handle_waitlist_actions",
    title: "Handle Waitlist Actions",
    source_file: "functions/handle_waitlist_actions.ts",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            channel_id: { type: Schema.slack.types.channel_id },
            selected_league: { type: Schema.types.string },
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
    state.off = action.action_id === "next_page"
        ? (state.off ?? 0) + ENTRIES_PER_PAGE
        : Math.max(0, (state.off ?? 0) - ENTRIES_PER_PAGE);

    const waitlists = await fetchWaitlists(env);
    await client.views.update({
        view_id: body.view?.id,
        view: buildListView(waitlists, state),
    });
});

handler.addViewSubmissionHandler(CALLBACK_ID, async ({ body, client, env }) => {
    const state = extractModalState<ModalState>(body);
    captureDropdownSelections(
        body,
        state as unknown as Record<string, unknown>,
        "sel",
        DROPDOWN_CAPTURE_CONFIG,
    );

    const selections = Object.entries(state.sel ?? {}).filter(
        ([, type]) => type === "admit" || type === "remove",
    );

    // deno-lint-ignore no-explicit-any
    const execId = (body as any).function_data?.execution_id;
    const complete = (actionsJson: string) =>
        execId
            ? client.functions.completeSuccess({
                function_execution_id: execId,
                outputs: { actions_json: actionsJson },
            })
            : Promise.resolve();

    if (selections.length === 0) {
        await complete("[]");
        return;
    }

    log("submit", { selections: selections.map(([row, type]) => `${type}:${row}`) });

    const [sport, day, division] = state.league.split("|");
    const league = toLeague(state.league);

    // Fresh fetch: selections reference sheet row numbers, so resolve against current data
    const waitlists = await fetchWaitlists(env);
    const byRow = new Map<number, WaitlistEntry>();
    for (const lw of Object.values(waitlists.leagues)) {
        for (const e of lw.entries) byRow.set(e.rowNumber, e);
    }

    // Resolve the Shopify waitlist tag once (admits only)
    let waitlistTag: string | null = null;
    if (selections.some(([, type]) => type === "admit")) {
        try {
            const leagueConfig = getLeague(sport, day, division);
            if (leagueConfig?.product_id) {
                const shopify = createShopifyClient(env);
                const handle = await getProductHandle(shopify, leagueConfig.product_id);
                if (handle) waitlistTag = `${handle}-waitlist`;
            }
        } catch (err) {
            console.error("[waitlist_actions] failed to get product handle:", err);
        }
    }

    const gmailClient = getOrCreateGoogleClient(env);

    const results: ActionResult[] = await Promise.all(
        selections.map(async ([rowStr, type]) => {
            const rowNumber = Number(rowStr);
            const entry = byRow.get(rowNumber);
            const r: ActionResult = {
                rowNumber,
                type: type as "admit" | "remove",
                name: `${entry?.firstName ?? ""} ${entry?.lastName ?? ""}`.trim() ||
                    `row ${rowNumber}`,
                firstName: entry?.firstName ?? "",
                email: entry?.emailAddress ?? "",
                phone: entry?.phoneNumber,
                league,
                shopifyOk: true,
                emailOk: true,
            };
            if (!entry || type !== "admit") return r;

            log("admit", { rowNumber, email: r.email });

            if (r.email && waitlistTag) {
                try {
                    const shopify = createShopifyClient(env);
                    const res = await findOrCreateCustomerWithTag(shopify, r.email, waitlistTag, {
                        firstName: entry.firstName ?? "",
                        lastName: entry.lastName ?? "",
                        ...(entry.phoneNumber ? { phone: entry.phoneNumber } : {}),
                    });
                    if (!res.ok) {
                        r.shopifyOk = false;
                        r.shopifyError = res.error;
                    }
                } catch (e) {
                    r.shopifyOk = false;
                    r.shopifyError = e instanceof Error ? e.message : String(e);
                    console.error(`[shopify:${rowNumber}]`, e);
                }
            }

            // Only email when the Shopify tag succeeded — the login link is useless without it
            if (r.shopifyOk && r.email) {
                try {
                    const emailRes = await sendEmail(
                        gmailClient,
                        buildWaitlistAdmitEmail(
                            { firstName: entry.firstName, emailAddress: entry.emailAddress },
                            league,
                        ),
                    );
                    if (!emailRes.ok) {
                        r.emailOk = false;
                        r.emailError = emailRes.error;
                    }
                } catch (e) {
                    r.emailOk = false;
                    r.emailError = e instanceof Error ? e.message : String(e);
                    console.error(`[email:${rowNumber}]`, e);
                }
            }

            return r;
        }),
    );

    const { text, blocks } = buildActionMessage(results, formatActionResult);
    await client.chat.postMessage({ channel: state.ch, text, blocks });

    const outputActions = results.map((r) => ({
        type: r.type,
        rowNumber: String(r.rowNumber),
        firstName: r.firstName,
        lastName: byRow.get(r.rowNumber)?.lastName ?? "",
        emailAddress: r.email,
        sport,
        day,
        division,
    }));
    await complete(JSON.stringify(outputActions));
});

handler.addViewClosedHandler(CALLBACK_ID, () => {});

export default handler;
