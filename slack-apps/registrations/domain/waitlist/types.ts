/** Waitlist data model: entry / league waitlist / email lookup index, plus the
 *  status-keyword constants the parser uses (case-insensitive substring match)
 *  and the small pure queries over those types. */

import type { League } from "../league/types.ts";

export const CancelledStatuses = ["cancelled", "expired"] as const;
export const RegisteredStatuses = ["registered", "signed"] as const;
export const ContactedStatuses = ["contacted"] as const;

export interface WaitlistEntry {
    rowNumber: number;
    position: number;
    createdAt: string;
    /** Full League identity. Populated by the parser using CURRENT_YEAR/CURRENT_SEASON
     *  + sport/day/division from the sheet. Single source of truth — never reconstruct. */
    league: League;
    firstName: string;
    lastName: string;
    emailAddress: string;
    phoneNumber?: string;
    gender?: string;
    pronouns?: string;
    status?: string;
}

export interface LeagueWaitlist {
    entries: WaitlistEntry[];
    total: number;
}

export interface EmailLookupEntry {
    leagueKey: string;
    entry: WaitlistEntry;
    total: number;
}

export interface LeagueWaitlists {
    leagues: Record<string, LeagueWaitlist>;
    byEmail: Record<string, EmailLookupEntry[]>;
    url: string;
    /** 0-based index of the Status column, resolved by the fetcher in the same
     *  HTTP call as the row data — so writers don't need a second round trip. */
    statusColumnIndex: number;
}

/** Wire contract for `actions_json` passed between waitlist workflow steps. */
export interface WaitlistAction {
    type: "admit" | "remove" | "order";
    rowNumber: string;
    firstName: string;
    lastName?: string;
    emailAddress: string;
    sport?: string;
    day?: string;
    division?: string;
}
