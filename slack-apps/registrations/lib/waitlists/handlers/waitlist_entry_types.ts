/** Keywords matched against the Status column (case-insensitive, substring match). */

export const CancelledStatuses = ["cancelled", "expired"] as const;

export const RegisteredStatuses = ["registered", "signed"] as const;

export const ContactedStatuses = ["contacted"] as const;

export interface WaitlistEntry {
    rowNumber: number;
    position: number;
    createdAt: string;
    sport: string;
    day: string;
    division: string;
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
}

import type { League } from "../../../types/league.ts";

export interface WaitlistSignup {
    rowNumber: number;
    createdAt: string;
    league: League;
    firstName: string;
    lastName: string;
    emailAddress: string;
    phoneNumber?: string;
    gender?: string;
    pronouns?: string;
    status?: string;
}

export interface CrossLeagueInfo {
    league: League;
    position: number;
    total: number;
}

export interface WaitlistSignupDisplay {
    rowNumber: number;
    firstName: string;
    lastName: string;
    emailAddress: string;
    phoneNumber?: string;
    gender?: string;
    pronouns?: string;
    position: number;
    createdAtFormatted: string;
    crossLeague: CrossLeagueInfo[];
}

export interface ProcessWaitlistSignupsState {
    ch: string;
    lg?: League;
    off?: number;
    sel?: Record<string, "admit" | "remove">;
}
