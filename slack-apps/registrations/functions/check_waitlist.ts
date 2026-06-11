import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";
import { ENTRIES_PER_PAGE, GOOGLE_SHEETS } from "../config.ts";
import { capitalize } from "../utils/formatters.ts";
import { getOrCreateGoogleClient } from "../lib/clients/google/client.ts";
import { parseWaitlistRows } from "../lib/waitlists/handlers/sheet_parser.ts";
import type {
    EmailLookupEntry,
    WaitlistEntry,
} from "../lib/waitlists/handlers/waitlist_entry_types.ts";

const SHEET = GOOGLE_SHEETS.waitlists;
const TAB = { name: SHEET.tab_name, id: SHEET.tab_id };

type Block = Record<string, unknown>;

const plainText = (text: string) => ({ type: "plain_text" as const, text });
const mrkdwn = (text: string) => ({ type: "mrkdwn" as const, text });

function formatLeagueLabel(leagueKey: string): string {
    const [sport, day, div] = leagueKey.split("|");
    return `${capitalize(sport)} - ${capitalize(day)} - ${
        div === "wtnb" ? "WTNB+" : "Open"
    } Division`;
}

function summaryText(total: number): string {
    if (total === 0) return "No one on waitlist";
    if (total === 1) return "1 person on waitlist";
    return `${total} people on waitlist`;
}

function entrySection(
    entry: WaitlistEntry,
    leagueKey: string,
    byEmail: Record<string, EmailLookupEntry[]>,
): Block {
    const fields = [
        mrkdwn(`*#${entry.position}*`),
        mrkdwn(`*Name:*\n${entry.firstName} ${entry.lastName}`),
        mrkdwn(`*Email:*\n${entry.emailAddress}`),
        mrkdwn(`*Status:*\n${entry.status || "Waiting"}`),
        mrkdwn(`*Submitted:*\n${entry.createdAt}`),
        mrkdwn(`*Pronouns:*\n${entry.pronouns || "N/A"}`),
    ];

    const others = (byEmail[entry.emailAddress.toLowerCase()] ?? []).filter(
        (e) => e.leagueKey !== leagueKey,
    );
    if (others.length > 0) {
        const labels = others
            .map((e) => `${formatLeagueLabel(e.leagueKey)} (#${e.entry.position}/${e.total})`)
            .join(", ");
        fields.push(mrkdwn(`*Also on:*\n${labels}`));
    }

    return { type: "section", fields };
}

export const CheckWaitlistFunction = DefineFunction({
    callback_id: "check_waitlist",
    title: "Check Waitlist",
    source_file: "functions/check_waitlist.ts",
    input_parameters: {
        properties: {
            interactivity: { type: Schema.slack.types.interactivity },
            selected_league: { type: Schema.types.string },
        },
        required: ["interactivity", "selected_league"],
    },
    output_parameters: { properties: {}, required: [] },
});

export default SlackFunction(CheckWaitlistFunction, async ({ inputs, client, env }) => {
    const google = getOrCreateGoogleClient(env);
    const { url, values } = await google.getSpreadsheet(SHEET.spreadsheet_id, TAB, "A1:J");
    const waitlists = parseWaitlistRows(values, url);

    const leagueKey = inputs.selected_league;
    const league = waitlists.leagues[leagueKey];
    const entries = league?.entries ?? [];
    const leagueLabel = formatLeagueLabel(leagueKey);

    const blocks: Block[] = [
        { type: "header", text: plainText(`${leagueLabel} Waitlist`) },
        { type: "context", elements: [mrkdwn(summaryText(entries.length))] },
        { type: "divider" },
    ];

    if (entries.length === 0) {
        blocks.push({
            type: "section",
            text: mrkdwn("_No waitlist entries found for this league._"),
        });
    } else {
        for (const entry of entries.slice(0, ENTRIES_PER_PAGE)) {
            blocks.push(entrySection(entry, leagueKey, waitlists.byEmail));
        }
        if (entries.length > ENTRIES_PER_PAGE) {
            blocks.push({
                type: "context",
                elements: [
                    mrkdwn(
                        `_Showing top ${ENTRIES_PER_PAGE} of ${entries.length}. View full list below._`,
                    ),
                ],
            });
        }
    }

    blocks.push({ type: "divider" });
    blocks.push({
        type: "actions",
        elements: [
            {
                type: "button",
                text: plainText("View Full Waitlist in Google Sheets"),
                url: waitlists.url,
            },
        ],
    });

    const openRes = await client.views.open({
        interactivity_pointer: inputs.interactivity.interactivity_pointer,
        view: {
            type: "modal",
            title: plainText("Waitlist"),
            close: plainText("Close"),
            blocks,
        },
    });
    if (!openRes.ok) return { error: `Failed to open modal: ${openRes.error}` };
    return { outputs: {} };
});
