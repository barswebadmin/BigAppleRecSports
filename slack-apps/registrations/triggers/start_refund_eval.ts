/**
 * Shortcut trigger for the new sheet-driven refund-evaluation flow.
 *
 * The slash command itself (`/eval-refund-request`) is registered via the
 * Slack CLI at deploy time (`slack triggers create`), targeting the
 * `validate_refund_request` workflow defined in
 * `workflows/validate_refund_request.ts`.
 */

import type { Trigger } from "deno-slack-sdk/types.ts";
import { TriggerContextData, TriggerTypes } from "deno-slack-api/mod.ts";
import ValidateRefundRequestWorkflow from "../workflows/validate_refund_request.ts";

const trigger: Trigger<typeof ValidateRefundRequestWorkflow.definition> = {
    type: TriggerTypes.Shortcut,
    name: "Evaluate Refund Request",
    description: "Pick an unprocessed refund request from the sheet and evaluate it",
    workflow: `#/workflows/${ValidateRefundRequestWorkflow.definition.callback_id}`,
    inputs: {
        interactivity: { value: TriggerContextData.Shortcut.interactivity },
        channel_id: { value: TriggerContextData.Shortcut.channel_id },
    },
};

export default trigger;
