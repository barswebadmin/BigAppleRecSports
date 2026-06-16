/**
 * Parse waitlist spreadsheet rows into LeagueWaitlists structure.
 * Pure function — no I/O, no Slack imports.
 * Row 0 is the header row; data starts at row 1.
 */

import { buildLeagueKey } from "../league_key.ts";
import type {
    EmailLookupEntry,
    LeagueWaitlist,
    LeagueWaitlists,
    WaitlistEntry,
} from "./waitlist_entry_types.ts";
import { CancelledStatuses, RegisteredStatuses } from "./waitlist_entry_types.ts";

const INACTIVE_KEYWORDS = [...CancelledStatuses, ...RegisteredStatuses];

function isActive(status: string | undefined): boolean {
    if (!status) return true;
    const norm = status.toLowerCase();
    return !INACTIVE_KEYWORDS.some((k) => norm.includes(k));
}

export function findColumn(headers: string[], keyword: string): number {
    const lower = keyword.toLowerCase();
    return headers.findIndex((h) => h.toLowerCase().includes(lower));
}

function col(row: string[], idx: number): string {
    return idx >= 0 ? (row[idx] || "").trim() : "";
}

export function parseWaitlistRows(rows: string[][], spreadsheetUrl: string): LeagueWaitlists {
    if (rows.length < 2) return { leagues: {}, byEmail: {}, url: spreadsheetUrl };

    const headers = rows[0];
    const c = {
        createdAt: findColumn(headers, "timestamp"),
        league: findColumn(headers, "league"),
        firstName: findColumn(headers, "first name"),
        lastName: findColumn(headers, "last name"),
        emailAddress: findColumn(headers, "email address"),
        phoneNumber: findColumn(headers, "phone number"),
        gender: findColumn(headers, "gender"),
        pronouns: findColumn(headers, "pronouns"),
        status: findColumn(headers, "status"),
    };

    const leagueMap = new Map<string, Omit<WaitlistEntry, "position">[]>();

    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        const status = col(row, c.status);
        if (!isActive(status)) continue;

        const leagueRaw = col(row, c.league);
        const parts = leagueRaw.split("-").map((s) => s.trim());
        if (parts.length < 3) continue;

        const sport = parts[0];
        const day = parts[1];
        const division = parts[2];
        const leagueKey = buildLeagueKey(sport, day, division);

        const entry: Omit<WaitlistEntry, "position"> = {
            rowNumber: i + 1,
            createdAt: col(row, c.createdAt),
            sport: sport.trim().toLowerCase(),
            day: day.trim().toLowerCase(),
            division: division.trim().slice(0, 4).toLowerCase(),
            firstName: col(row, c.firstName),
            lastName: col(row, c.lastName),
            emailAddress: col(row, c.emailAddress).toLowerCase(),
            phoneNumber: col(row, c.phoneNumber) || undefined,
            gender: col(row, c.gender) || undefined,
            pronouns: col(row, c.pronouns) || undefined,
            status: status || undefined,
        };

        if (!leagueMap.has(leagueKey)) leagueMap.set(leagueKey, []);
        leagueMap.get(leagueKey)!.push(entry);
    }

    const leagues: Record<string, LeagueWaitlist> = {};
    const byEmail: Record<string, EmailLookupEntry[]> = {};

    for (const [leagueKey, rawEntries] of leagueMap) {
        const sorted = rawEntries.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
        const entries: WaitlistEntry[] = sorted.map((e, idx) => ({ ...e, position: idx + 1 }));
        const total = entries.length;
        leagues[leagueKey] = { entries, total };

        for (const entry of entries) {
            const email = entry.emailAddress;
            if (!byEmail[email]) byEmail[email] = [];
            byEmail[email].push({ leagueKey, entry, total });
        }
    }

    return { leagues, byEmail, url: spreadsheetUrl };
}
