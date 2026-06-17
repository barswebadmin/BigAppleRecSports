/** Workflow registry: which Google sheet each workflow reads, where its Slack
 *  channels come from, and where league identity is sourced. */

import { envOr } from "./env.ts";
import { REFUND_REVIEW_CHANNEL, REFUND_TEST_CHANNEL } from "./refunds.ts";

export type WorkflowName = "waitlist" | "refund";

export interface SheetRef {
    spreadsheet_id: string;
    tab_name: string;
    tab_id: string;
}

export interface WorkflowConfig {
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
        channels: { source: "static", test: REFUND_TEST_CHANNEL, review: REFUND_REVIEW_CHANNEL },
        leagueSource: "shopify",
    },
};

/** Resolve a workflow's sheet from the single workflow table. */
export function getWorkflowSheet(workflow: WorkflowName): SheetRef {
    return WORKFLOWS[workflow].sheet;
}
