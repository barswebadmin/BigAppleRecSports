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
