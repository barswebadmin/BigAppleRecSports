/** Slack Run-on-Slack workflow plumbing — completing executions, reading the
 *  envelope fields every handler needs. One copy of the boilerplate for all
 *  handlers; no `function_data.execution_id` lookups inlined in functions/. */

import type { SlackAPIClient } from "deno-slack-api/types.ts";

/** The Slack body envelope passed to block_actions / view_submission handlers.
 *  Typed `unknown` and accessed defensively so handlers don't need to widen
 *  the SDK type themselves. */
// deno-lint-ignore no-explicit-any
type SlackBody = any;

/** Workflow execution id from the body envelope. Absent in unit tests that
 *  don't simulate the SDK; callers must tolerate `undefined`. */
export function executionId(body: SlackBody): string | undefined {
    return body.function_data?.execution_id;
}

/** Slack user id of whoever clicked the action or submitted the view. */
export function processorUserId(body: SlackBody): string | undefined {
    return body.user?.id;
}

/** Bind a `(actionsJson) => Promise<...>` completer to this execution. When the
 *  body lacks an execution id (unit test envelope), the completer is a no-op. */
export function makeWorkflowCompleter(
    client: SlackAPIClient,
    body: SlackBody,
): (actionsJson: string) => Promise<unknown> {
    const execId = executionId(body);
    return (actionsJson) =>
        execId
            ? client.functions.completeSuccess({
                function_execution_id: execId,
                outputs: { actions_json: actionsJson },
            })
            : Promise.resolve();
}

/** Convenience: complete the current execution with an empty actions payload.
 *  Used by handlers that exit via "no admittable rows" or modal-cancel paths. */
export function completeWithEmpty(
    client: SlackAPIClient,
    body: SlackBody,
): Promise<unknown> {
    return makeWorkflowCompleter(client, body)("[]");
}
