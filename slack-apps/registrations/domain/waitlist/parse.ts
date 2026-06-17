/** Parse waitlist spreadsheet rows into a `LeagueWaitlists` structure. Pure —
 *  no I/O, no Slack imports. Row 0 is the header; data starts at row 1. */

import { CURRENT_SEASON, CURRENT_YEAR } from "../league/catalog.ts";
import { buildLeagueKey } from "../league/key.ts";
import type { EmailLookupEntry, LeagueWaitlist, LeagueWaitlists, WaitlistEntry } from "./types.ts";
import { CancelledStatuses, RegisteredStatuses } from "./types.ts";

const INACTIVE_KEYWORDS = [...CancelledStatuses, ...RegisteredStatuses];

interface ColumnIndex {
    createdAt: number;
    league: number;
    firstName: number;
    lastName: number;
    emailAddress: number;
    phoneNumber: number;
    gender: number;
    pronouns: number;
    status: number;
}

interface ParsedRow {
    leagueKey: string;
    entry: Omit<WaitlistEntry, "position">;
}

function isActive(status: string | undefined): boolean {
    if (!status) return true;
    const norm = status.toLowerCase();
    return !INACTIVE_KEYWORDS.some((k) => norm.includes(k));
}

function findColumn(headers: string[], keyword: string): number {
    const lower = keyword.toLowerCase();
    return headers.findIndex((h) => h.toLowerCase().includes(lower));
}

function col(row: string[], idx: number): string {
    return idx >= 0 ? (row[idx] || "").trim() : "";
}

/** Field-name → header keyword the parser searches for. The header may carry
 *  extra words ("Email Address (work)") — `findColumn` does a substring match. */
const COLUMN_KEYWORDS: Record<keyof ColumnIndex, string> = {
    createdAt: "timestamp",
    league: "league",
    firstName: "first name",
    lastName: "last name",
    emailAddress: "email address",
    phoneNumber: "phone number",
    gender: "gender",
    pronouns: "pronouns",
    status: "status",
};

function buildColumnIndex(headers: string[]): ColumnIndex {
    return Object.fromEntries(
        Object.entries(COLUMN_KEYWORDS).map(([field, kw]) => [field, findColumn(headers, kw)]),
    ) as unknown as ColumnIndex;
}

/** Project one sheet row into a `ParsedRow` or `null` (inactive / malformed
 *  league cell). `rowNumber` is 1-based to match what Sheets shows. */
function parseRow(row: string[], rowNumber: number, c: ColumnIndex): ParsedRow | null {
    const status = col(row, c.status);
    if (!isActive(status)) return null;
    const parts = col(row, c.league).split("-").map((s) => s.trim());
    if (parts.length < 3) return null;

    const sport = parts[0].toLowerCase();
    const day = parts[1].toLowerCase();
    const division = parts[2].slice(0, 4).toLowerCase();

    return {
        leagueKey: buildLeagueKey(sport, day, division),
        entry: {
            rowNumber,
            createdAt: col(row, c.createdAt),
            league: { year: CURRENT_YEAR, season: CURRENT_SEASON, sport, day, division },
            firstName: col(row, c.firstName),
            lastName: col(row, c.lastName),
            emailAddress: col(row, c.emailAddress).toLowerCase(),
            phoneNumber: col(row, c.phoneNumber) || undefined,
            gender: col(row, c.gender) || undefined,
            pronouns: col(row, c.pronouns) || undefined,
            status: status || undefined,
        },
    };
}

/** Group `ParsedRow`s by `leagueKey`, sort each group by created-at, and assign
 *  positions starting at 1. */
function groupByLeague(parsed: ParsedRow[]): Record<string, LeagueWaitlist> {
    const groups: Record<string, Omit<WaitlistEntry, "position">[]> = {};
    parsed.forEach(({ leagueKey, entry }) => (groups[leagueKey] ??= []).push(entry));

    return Object.fromEntries(
        Object.entries(groups).map(([leagueKey, raws]) => [leagueKey, toLeagueWaitlist(raws)]),
    );
}

function toLeagueWaitlist(raws: Omit<WaitlistEntry, "position">[]): LeagueWaitlist {
    const sorted = raws.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
    const entries: WaitlistEntry[] = sorted.map((e, idx) => ({ ...e, position: idx + 1 }));
    return { entries, total: entries.length };
}

/** Build the email → leagues index from the assembled leagues. Single flatMap
 *  pass — no nested loops. */
function buildEmailIndex(
    leagues: Record<string, LeagueWaitlist>,
): Record<string, EmailLookupEntry[]> {
    const flat: EmailLookupEntry[] = Object.entries(leagues).flatMap((
        [leagueKey, { entries, total }],
    ) => entries.map((entry) => ({ leagueKey, entry, total })));

    const byEmail: Record<string, EmailLookupEntry[]> = {};
    flat.forEach((lookup) => (byEmail[lookup.entry.emailAddress] ??= []).push(lookup));
    return byEmail;
}

export function parseWaitlistRows(rows: string[][], spreadsheetUrl: string): LeagueWaitlists {
    if (rows.length < 2) {
        return { leagues: {}, byEmail: {}, url: spreadsheetUrl, statusColumnIndex: -1 };
    }
    const columns = buildColumnIndex(rows[0]);
    const parsed = rows
        .slice(1)
        .map((row, idx) => parseRow(row, idx + 2, columns))
        .filter((p): p is ParsedRow => p !== null);

    const leagues = groupByLeague(parsed);
    const byEmail = buildEmailIndex(leagues);
    return { leagues, byEmail, url: spreadsheetUrl, statusColumnIndex: columns.status };
}
