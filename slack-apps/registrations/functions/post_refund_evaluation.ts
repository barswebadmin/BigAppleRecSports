/** Workflow boundary for the refund-evaluation review flow. Thin SDK wiring;
 *  every concern lives in `domain/refund/`. */

import type { SlackAPIClient } from "deno-slack-api/types.ts";
import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";

import {
    ACTION_ACTION_ID,
    AMOUNT_ACTION_ID,
    APPROVE_MODAL_CALLBACK_ID,
    type ApproveModalMeta,
} from "../views/refund/approve_modal.ts";
import { APPROVE_ACTION_ID, DENY_ACTION_ID } from "../views/refund/eval_blocks.ts";
import {
    handleApproveButton,
    handleApproveModalBlockAction,
    handleApproveModalSubmit,
    handleDenyButton,
    parsePayload,
    runPostRefundEvaluation,
} from "../domain/refund/orchestrator.ts";
import type { RefundEvaluationPayload } from "../domain/refund/types.ts";

// Re-exported for in-process regression tests — keeps the previous public
// surface the tests reach for; the orchestrator is the implementation.
export { runPostRefundEvaluation } from "../domain/refund/orchestrator.ts";

/** Parse the evaluation payload once and hand it to the handler; on bad JSON
 *  the handler is skipped (the Lambda already retries on parse failures). */
async function withParsedPayload(
    rawJson: string,
    fn: (payload: RefundEvaluationPayload) => Promise<void>,
): Promise<void> {
    const payload = parsePayload(rawJson);
    if (payload) await fn(payload);
}

const APPROVE_MODAL_INTERACTIVE_IDS = new RegExp(`^(${ACTION_ACTION_ID}|${AMOUNT_ACTION_ID})$`);

/** Function step inputs (matches `PostRefundEvaluationFunction` input_parameters). */
type PostRefundEvaluationInputs = { evaluation_json: string };

/** Block action on the review **message** (Approve / Deny). */
type RefundChannelBlockBody = {
    container: { channel_id: string; message_ts: string };
    user: { id: string };
    interactivity: { interactivity_pointer: string };
    function_data: { execution_id: string };
};

/** Block action inside the approval **modal** (action / amount dispatch). */
type RefundModalBlockBody = {
    user: { id: string };
    view?: {
        id?: string;
        private_metadata?: string;
        state?: { values?: Record<string, Record<string, unknown>> };
    };
};

/** View submission for the approval modal. */
type RefundViewSubmissionBody = {
    user: { id: string };
    function_data: { execution_id: string };
};

function asChannelBlockBody(body: unknown): RefundChannelBlockBody {
    return body as RefundChannelBlockBody;
}

function asModalBlockBody(body: unknown): RefundModalBlockBody {
    return body as RefundModalBlockBody;
}

function asViewSubmission(
    args: unknown,
): {
    inputs: PostRefundEvaluationInputs;
    body: RefundViewSubmissionBody;
    view: {
        private_metadata?: string;
        state?: { values?: Record<string, Record<string, unknown>> };
    };
    client: SlackAPIClient;
} {
    return args as {
        inputs: PostRefundEvaluationInputs;
        body: RefundViewSubmissionBody;
        view: {
            private_metadata?: string;
            state?: { values?: Record<string, Record<string, unknown>> };
        };
        client: SlackAPIClient;
    };
}

export const PostRefundEvaluationFunction = DefineFunction({
    callback_id: "post_refund_evaluation",
    title: "Post Refund Evaluation",
    description: "Receives the Lambda's refund evaluation payload and posts the review message",
    source_file: "functions/post_refund_evaluation.ts",
    input_parameters: {
        properties: {
            evaluation_json: {
                type: Schema.types.string,
                description: "JSON-serialised RefundEvaluationPayload from the Lambda",
            },
        },
        required: ["evaluation_json"],
    },
    output_parameters: {
        properties: {
            message_ts: { type: Schema.types.string },
            channel_id: { type: Schema.types.string },
        },
        required: ["message_ts", "channel_id"],
    },
});

export default SlackFunction(
    PostRefundEvaluationFunction,
    ({ inputs, client }: { inputs: PostRefundEvaluationInputs; client: SlackAPIClient }) =>
        runPostRefundEvaluation(inputs, client),
)
    .addBlockActionsHandler(
        APPROVE_ACTION_ID,
        async (ctx: unknown) => {
            const { inputs, body, client } = ctx as {
                inputs: PostRefundEvaluationInputs;
                body: unknown;
                client: SlackAPIClient;
            };
            const b = asChannelBlockBody(body);
            await withParsedPayload(inputs.evaluation_json, async (payload) => {
                await handleApproveButton(payload, {
                    channel: b.container.channel_id,
                    messageTs: b.container.message_ts,
                    interactivityPointer: b.interactivity.interactivity_pointer,
                    userId: b.user.id,
                }, client);
            });
        },
    )
    .addBlockActionsHandler(
        DENY_ACTION_ID,
        async (ctx: unknown) => {
            const { inputs, body, client } = ctx as {
                inputs: PostRefundEvaluationInputs;
                body: unknown;
                client: SlackAPIClient;
            };
            const b = asChannelBlockBody(body);
            await withParsedPayload(inputs.evaluation_json, async (payload) => {
                await handleDenyButton(payload, {
                    userId: b.user.id,
                    channel: b.container.channel_id,
                    messageTs: b.container.message_ts,
                    executionId: b.function_data.execution_id,
                }, client);
            });
        },
    )
    .addBlockActionsHandler(
        APPROVE_MODAL_INTERACTIVE_IDS,
        async (ctx: unknown) => {
            const { inputs, body, client } = ctx as {
                inputs: PostRefundEvaluationInputs;
                body: unknown;
                client: SlackAPIClient;
            };
            const b = asModalBlockBody(body);
            await withParsedPayload(inputs.evaluation_json, async (payload) => {
                const view = b.view;
                if (!view?.id) return;
                const meta = JSON.parse(view.private_metadata || "{}") as ApproveModalMeta;
                await handleApproveModalBlockAction(payload, {
                    userId: b.user.id,
                    viewId: view.id,
                    values: view.state?.values ?? {},
                    meta,
                }, client);
            });
        },
    )
    .addViewSubmissionHandler(
        APPROVE_MODAL_CALLBACK_ID,
        async (ctx: unknown) => {
            const { inputs, body, view, client } = asViewSubmission(ctx);
            const payload = parsePayload(inputs.evaluation_json);
            if (!payload) return;
            return await handleApproveModalSubmit(payload, {
                userId: body.user.id,
                executionId: body.function_data.execution_id,
                meta: JSON.parse(view.private_metadata || "{}") as ApproveModalMeta,
                stateValues: view.state?.values ?? {},
            }, client);
        },
    );
