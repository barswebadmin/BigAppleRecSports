/** Waitlist list-modal view builders. The handler delegates the entire view
 *  shape (title, empty/populated branching, per-entry rendering, pagination,
 *  per-row email checkbox) to these builders. UI-side block/action id contract
 *  also lives here. */

import { buildListModal } from "../../shared/slack/list_modal.ts";
import type { SlackView } from "../../shared/slack/message.ts";
import { capitalize } from "../../shared/text/strings.ts";
import { formatDivision } from "../../domain/league/format.ts";
import { leagueFromKey } from "../../domain/league/identity.ts";
import { isContacted } from "../../domain/waitlist/predicates.ts";
import type { LeagueWaitlists, WaitlistEntry } from "../../domain/waitlist/types.ts";
import { formatEntryContextLines, formatEntryTitle, formatReadOnlyEntry } from "./format.ts";

export const CALLBACK_ID = "handle_waitlist_actions";

/** Per-row dropdown options shown next to each waitlist entry. */
export const ACTION_OPTIONS = [
    { label: "No changes", value: "none" },
    { label: "Admit", value: "admit" },
    { label: "Remove", value: "remove" },
];

/** Page size for the waitlist list modal — drives Back/Next offset arithmetic. */
export const ENTRIES_PER_PAGE = 3;

// Slack block/action id contract for the list modal. The builders below mint
// these ids per row; the handler scans inbound block actions by the same
// prefixes to fold them back into modal state.
export const ACTION_PREFIX_DROPDOWN = "action_r";
export const ACTION_PREFIX_CHECKBOX = "email_r";

/** Dropdown values that mean "no admit/remove decision". `skip` is a legacy
 *  alias kept for back-compat with older `private_metadata` blobs. */
export const NO_ACTION_DROPDOWN_VALUES = ["none", "skip"];

/** Persisted modal state (private_metadata). */
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

/** Slack caps modal titles at 24 chars; `Waitlist for {Day3} {SPORT2} {Open|WTNB}`.
 *  The full unabbreviated league + division sits in the modal's sub-line. */
export function buildModalTitle(sport: string, day: string, division: string): string {
    const day3 = capitalize(day.slice(0, 3));
    const sportAbbr = SPORT_ABBR[sport] ?? capitalize(sport).slice(0, 2);
    const divTitle = division === "wtnb" ? "WTNB" : "Open";
    return `Waitlist for ${day3} ${sportAbbr} ${divTitle}`;
}

const LIST_INSTRUCTION =
    "Select *Admit* to let people off the waitlist, or *Remove* if they are no longer waiting (update any selection to *No Changes* if it was accidental). Their Shopify profile(s) will be updated (or created) with a tag that unlocks the reg page as long as they're logged in. Click *Back*/*Next* at the bottom of the window to go backwards/forwards and see more waitlist entries.";

// Row-id minting — single source of truth for the block/action ids each entry
// contributes to the modal.
function entryBlockId(e: WaitlistEntry): string {
    return `entry_r${e.rowNumber}`;
}

function entryDropdownActionId(e: WaitlistEntry): string {
    return `${ACTION_PREFIX_DROPDOWN}${e.rowNumber}`;
}

function entryCheckboxBlockId(e: WaitlistEntry): string {
    return `email_block_r${e.rowNumber}`;
}

function entryCheckboxActionId(e: WaitlistEntry): string {
    return `${ACTION_PREFIX_CHECKBOX}${e.rowNumber}`;
}

function emailCheckboxOption(e: WaitlistEntry): { label: string; value: string } {
    return { label: `Notify via email (${e.emailAddress})`, value: "email" };
}

// ============================================================================

// ============================================================================

/** Empty-waitlist modal: title + close-only + an explanatory empty message. */
export function buildEmptyWaitlistView(args: {
    title: string;
    sport: string;
    day: string;
    state: ModalState;
}): SlackView {
    return buildListModal<WaitlistEntry>({
        callbackId: CALLBACK_ID,
        title: args.title,
        closeLabel: "Close",
        items: [],
        offset: 0,
        pageSize: ENTRIES_PER_PAGE,
        formatItemTitle: () => "",
        getItemId: (e) => e.rowNumber,
        getBlockId: entryBlockId,
        getActionId: entryDropdownActionId,
        actionOptions: ACTION_OPTIONS,
        paginationActionIds: { prev: "prev_page", next: "next_page" },
        metadata: JSON.stringify(args.state),
        emptyMessage: `Waitlist for *${capitalize(args.day)} ${
            capitalize(args.sport)
        }* is detected to be empty. If you believe this is incorrect, please reach out to the web team.`,
    });
}

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
}): SlackView {
    const { title, sport, day, division, state, waitlists, entries, total } = args;
    return buildListModal<WaitlistEntry>({
        callbackId: CALLBACK_ID,
        title,
        submitLabel: "Submit",
        closeLabel: "Cancel",
        headerText: `${total} ${total === 1 ? "person" : "people"} on the waitlist`,
        subText: `${state.dry ? "DRY RUN ONLY — " : ""}Waitlist for ${capitalize(day)} ${
            capitalize(sport)
        } (${formatDivision(division, "label")})`,
        instructionText: LIST_INSTRUCTION,
        items: entries,
        offset: state.off ?? 0,
        pageSize: ENTRIES_PER_PAGE,
        formatItemTitle: (e) => formatEntryTitle(e),
        formatItemContextLines: (e) => formatEntryContextLines(e, state.league, waitlists.byEmail),
        getItemId: (e) => e.rowNumber,
        getBlockId: entryBlockId,
        getActionId: entryDropdownActionId,
        actionOptions: ACTION_OPTIONS,
        paginationActionIds: { prev: "prev_page", next: "next_page" },
        existingSelections: state.sel,
        checkbox: {
            getBlockId: entryCheckboxBlockId,
            getActionId: entryCheckboxActionId,
            getOption: emailCheckboxOption,
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
): SlackView {
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
