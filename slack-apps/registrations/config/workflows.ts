/** Workflow registry: which Google sheet each workflow reads, where its Slack
 *  channels come from, and where league identity is sourced. */

import { envOr } from "./store.ts";

type WorkflowName = "waitlist" | "refund";

interface SheetRef {
    spreadsheet_id: string;
    tab_name: string;
    tab_id: string;
}

interface WorkflowConfig {
    sheet: SheetRef;
    /** Where the workflow's Slack channel is resolved from. */
    channels:
        | { source: "per_league" }
        | { source: "static"; test: string; review: string };
    /** Where league identity comes from. */
    leagueSource: "config" | "shopify";
}

export const WORKFLOWS: Record<WorkflowName, WorkflowConfig> = {
    waitlist: {
        sheet: {
            spreadsheet_id: envOr(
                "WAITLIST_SHEET_ID",
                "1QgyHDN9EcxqefEJCDozfLZ7QKVxSbOaW28WOET9PYEE",
            ),
            tab_name: "Form Responses 1",
            tab_id: "2072632661",
        },
        channels: { source: "per_league" },
        leagueSource: "config",
    },
    refund: {
        sheet: {
            spreadsheet_id: envOr(
                "REFUND_SHEET_ID",
                "11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw",
            ),
            tab_name: "Refund_Requests",
            tab_id: "1435845892",
        },
        channels: {
            source: "static",
            test: envOr("REFUND_TEST_CHANNEL", "#joe-test"),
            review: envOr("REFUND_REVIEW_CHANNEL", "#exec-leadership-2026"),
        },
        leagueSource: "shopify",
    },
};

/** Resolve a workflow's static test/review channel pair, throwing if the
 *  workflow is configured for a different routing mode (e.g. `per_league`). */
export function getStaticChannels(workflow: WorkflowName): { test: string; review: string } {
    const ch = WORKFLOWS[workflow].channels;
    if (ch.source !== "static") {
        throw new Error(
            `Workflow '${workflow}' is not configured with static channels (source=${ch.source})`,
        );
    }
    return { test: ch.test, review: ch.review };
}
