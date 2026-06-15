import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { fetchWaitlists } from "../lib/waitlists/sheet_service.ts";

export const FetchCurrentWaitlistsFunction = DefineFunction({
    callback_id: "fetch_current_waitlists",
    title: "Fetch Current Waitlists",
    source_file: "functions/fetch_current_waitlists.ts",
    input_parameters: {
        properties: {},
        required: [],
    },
    output_parameters: {
        properties: {
            waitlists_json: { type: Schema.types.string },
        },
        required: ["waitlists_json"],
    },
});

export default SlackFunction(FetchCurrentWaitlistsFunction, async ({ env }) => {
    try {
        const waitlists = await fetchWaitlists(env);

        // Summary
        const leagueKeys = Object.keys(waitlists.leagues);
        const totalEntries = Object.values(waitlists.leagues).reduce((sum, l) => sum + l.total, 0);
        const uniqueEmails = Object.keys(waitlists.byEmail).length;
        console.log(
            `[fetch_waitlists] ${leagueKeys.length} leagues, ${totalEntries} active entries, ${uniqueEmails} unique emails`,
        );

        // Print each league with count and first 2 entries
        for (const key of leagueKeys) {
            const league = waitlists.leagues[key];
            console.log(`\n[league: ${key}] ${league.total} entries`);
            for (const entry of league.entries.slice(0, 2)) {
                console.log(
                    `  #${entry.position} row=${entry.rowNumber} ${entry.firstName} ${entry.lastName} (${entry.emailAddress}) created=${entry.createdAt}`,
                );
            }
            if (league.total > 2) console.log(`  ... and ${league.total - 2} more`);
        }

        // Print a sample email lookup (first email with 2+ leagues)
        const multiLeagueEmail = Object.entries(waitlists.byEmail).find(
            ([, entries]) => entries.length > 1,
        );
        if (multiLeagueEmail) {
            const [email, entries] = multiLeagueEmail;
            console.log(`\n[byEmail sample: ${email}] on ${entries.length} leagues:`);
            for (const e of entries) {
                console.log(`  ${e.leagueKey} #${e.entry.position}/${e.total}`);
            }
        }

        return {
            outputs: {
                waitlists_json: JSON.stringify(waitlists),
            },
        };
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[fetch_waitlists] ${msg}`);
        return {
            outputs: {
                waitlists_json: JSON.stringify({ leagues: {}, byEmail: {}, url: "" }),
            },
        };
    }
});
