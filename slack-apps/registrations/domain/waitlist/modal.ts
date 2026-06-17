/** Waitlist list-modal view builders. The handler delegates the entire view
 *  shape (title, empty/populated branching, per-entry rendering, pagination,
 *  per-row email checkbox) to these builders. Predicates/types specific to the
 *  list modal also live here. */

import { ACTION_OPTIONS, ENTRIES_PER_PAGE } from "../../config/slack.ts";
import { buildListModal } from "../../shared/slack/list_modal.ts";
import { capitalize } from "../../shared/text/strings.ts";
import { formatDivisionLabel } from "../league/format.ts";
import { leagueFromKey } from "../league/key.ts";
import { formatEntryContextLines, formatEntryTitle, formatReadOnlyEntry } from "./display.ts";
import { ContactedStatuses, type LeagueWaitlists, type WaitlistEntry } from "./types.ts";

export const CALLBACK_ID = "handle_waitlist_actions";

/** Persisted modal state (private_metadata). The handler is the sole consumer
 *  of the action callbacks that read/write it; declared here because the modal
 *  builders embed it in their `metadata` payload. */
export interface ModalState {
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

export function isContacted(entry: WaitlistEntry): boolean {
    if (!entry.status) return false;
    const norm = entry.status.toLowerCase();
    return ContactedStatuses.some((k) => norm.includes(k));
}

/** Slack caps modal titles at 24 chars, so the title abbreviates everything:
 *  `Waitlist for {Day3} {SPORT2} {Open|WTNB}`. The `+` is dropped from WTNB+
 *  because it would push the longest combos to 25 chars. The full,
 *  unabbreviated `Waitlist for {Day} {Sport} ({Division})` lives in the
 *  modal's sub-line. */
export function buildModalTitle(sport: string, day: string, division: string): string {
    const day3 = capitalize(day.slice(0, 3));
    const sportAbbr = SPORT_ABBR[sport] ?? capitalize(sport).slice(0, 2);
    const divTitle = division === "wtnb" ? "WTNB" : "Open";
    return `Waitlist for ${day3} ${sportAbbr} ${divTitle}`;
}

/** Empty-waitlist modal: title + close-only + an explanatory empty message. */
export function buildEmptyWaitlistView(args: {
    title: string;
    sport: string;
    day: string;
    state: ModalState;
}): Record<string, unknown> {
    const dayLabel = capitalize(args.day);
    const sportLabel = capitalize(args.sport);
    return buildListModal<WaitlistEntry>({
        callbackId: CALLBACK_ID,
        title: args.title,
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
        metadata: JSON.stringify(args.state),
        emptyMessage:
            `Waitlist for *${dayLabel} ${sportLabel}* is detected to be empty. If you believe this is incorrect, please reach out to the web team.`,
    });
}

const LIST_INSTRUCTION =
    "Select *Admit* to let people off the waitlist, or *Remove* if they are no longer waiting (update any selection to *No Changes* if it was accidental). Their Shopify profile(s) will be updated (or created) with a tag that unlocks the reg page as long as they're logged in. Click *Back*/*Next* at the bottom of the window to go backwards/forwards and see more waitlist entries.";

/** Populated-waitlist modal: per-entry dropdown + email checkbox + pagination. */
export function buildPopulatedWaitlistView(args: {
    title: string;
    sport: string;
    day: string;
    division: string;
    state: ModalState;
    waitlists: LeagueWaitlists;
    entries: WaitlistEntry[];
    total: number;
}): Record<string, unknown> {
    const { title, sport, day, division, state, waitlists, entries, total } = args;
    // Count stands out as a big-bold header; full league + division (which can't
    // fit the 24-char title) sits in the smaller sub-line.
    const headerText = `${total} ${total === 1 ? "person" : "people"} on the waitlist`;
    const subText = `${state.dry ? "DRY RUN ONLY — " : ""}Waitlist for ${capitalize(day)} ${
        capitalize(sport)
    } (${formatDivisionLabel(division)})`;

    return buildListModal<WaitlistEntry>({
        callbackId: CALLBACK_ID,
        title,
        submitLabel: "Submit",
        closeLabel: "Cancel",
        headerText,
        subText,
        instructionText: LIST_INSTRUCTION,
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

/** Top-level view router: empty vs populated, derived from the current state. */
export function buildListView(
    waitlists: LeagueWaitlists,
    state: ModalState,
): Record<string, unknown> {
    const { sport, day, division } = leagueFromKey(state.league);
    const title = buildModalTitle(sport, day, division);
    const league = waitlists.leagues[state.league];
    const entries = league?.entries ?? [];
    const total = league?.total ?? 0;

    if (entries.length === 0) return buildEmptyWaitlistView({ title, sport, day, state });
    return buildPopulatedWaitlistView({
        title,
        sport,
        day,
        division,
        state,
        waitlists,
        entries,
        total,
    });
}
