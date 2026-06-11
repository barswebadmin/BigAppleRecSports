import { DefineWorkflow, Schema } from "deno-slack-sdk/mod.ts";
import { FetchCurrentWaitlistsFunction } from "../functions/fetch_current_waitlists.ts";
import { ResolveWaitlistOrderFunction } from "../functions/resolve_waitlist_order.ts";
import { UpdateWaitlistSpreadsheetFunction } from "../functions/update_waitlist_spreadsheet.ts";

const ReceiveWaitlistOrderWorkflow = DefineWorkflow({
    callback_id: "receive_waitlist_order",
    title: "Receive Waitlist Order",
    description: "Webhook — receives a waitlist order and marks the entry as registered",
    input_parameters: {
        properties: {
            body: { type: Schema.types.string },
        },
        required: ["body"],
    },
});

const fetchStep = ReceiveWaitlistOrderWorkflow.addStep(FetchCurrentWaitlistsFunction, {});

const resolveStep = ReceiveWaitlistOrderWorkflow.addStep(ResolveWaitlistOrderFunction, {
    body: ReceiveWaitlistOrderWorkflow.inputs.body,
    waitlists_json: fetchStep.outputs.waitlists_json,
});

ReceiveWaitlistOrderWorkflow.addStep(UpdateWaitlistSpreadsheetFunction, {
    actions_json: resolveStep.outputs.actions_json,
});

export default ReceiveWaitlistOrderWorkflow;
