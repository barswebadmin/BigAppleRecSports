/** Console-only diagnostic summaries. Kept separate from the workflow handler
 *  so the handler stays a thin passthrough and so this log surface is callable
 *  from a future CLI or test without touching SDK plumbing. */

import type { LeagueWaitlist, LeagueWaitlists, WaitlistEntry } from "./types.ts";

/** Print a per-league rollup of counts and the first two entries, plus a
 *  byEmail sample if any single email appears on more than one league. */
export function logWaitlistsSummary(waitlists: LeagueWaitlists): void {
    const leagues = Object.entries(waitlists.leagues);
    const totalEntries = leagues.reduce((sum, [, lw]) => sum + lw.total, 0);
    const uniqueEmails = Object.keys(waitlists.byEmail).length;
    console.log(
        `[fetch_waitlists] ${leagues.length} leagues, ${totalEntries} active entries, ${uniqueEmails} unique emails`,
    );

    leagues.flatMap(formatLeagueLines).forEach((line) => console.log(line));

    const sample = Object.entries(waitlists.byEmail).find(([, entries]) => entries.length > 1);
    if (!sample) return;
    const [email, entries] = sample;
    console.log(`\n[byEmail sample: ${email}] on ${entries.length} leagues:`);
    entries.forEach((e) => console.log(`  ${e.leagueKey} #${e.entry.position}/${e.total}`));
}

/** Header line + up to two preview entries + "and N more" tail for one league. */
function formatLeagueLines([key, league]: [string, LeagueWaitlist]): string[] {
    const preview = league.entries.slice(0, 2).map(formatEntryPreview);
    const tail = league.total > 2 ? [`  ... and ${league.total - 2} more`] : [];
    return [`\n[league: ${key}] ${league.total} entries`, ...preview, ...tail];
}

const formatEntryPreview = (e: WaitlistEntry): string =>
    `  #${e.position} row=${e.rowNumber} ${e.firstName} ${e.lastName} (${e.emailAddress}) created=${e.createdAt}`;
