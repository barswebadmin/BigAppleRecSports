/** Modal `private_metadata` state helpers — generic over state shape. The
 *  capture helpers return the merged selection map so callers can assign it to
 *  a specifically-typed state field without any unsound `as unknown as` cast. */

// deno-lint-ignore no-explicit-any
type SlackBody = any;

export function extractModalState<S>(body: SlackBody): S {
    return JSON.parse(body.view?.private_metadata || "{}");
}

/** Flatten Slack's nested `view.state.values` (block → action → action-state)
 *  into a single `(actionId, actionState)` stream. */
function flattenActions<A>(values: Record<string, Record<string, A>>): [string, A][] {
    return Object.values(values).flatMap((block) => Object.entries(block));
}

/** Merge the visible page's actions into a persistent selections map. One
 *  pipeline for every action shape — pass in how to read the value and what
 *  counts as "clear this item". `view.state` only holds currently-rendered
 *  blocks, so callers run this before every pagination and on submit. */
function captureSelections<A, V>(
    body: SlackBody,
    prior: Record<string, V> | undefined,
    actionIdPrefix: string,
    extractValue: (action: A) => V | undefined,
    shouldClear: (value: V | undefined) => boolean,
): Record<string, V> {
    const selections: Record<string, V> = { ...(prior ?? {}) };
    flattenActions<A>(body.view?.state?.values ?? {})
        .filter(([actionId]) => actionId.startsWith(actionIdPrefix))
        .forEach(([actionId, action]) => {
            const itemId = actionId.slice(actionIdPrefix.length);
            const value = extractValue(action);
            if (shouldClear(value)) delete selections[itemId];
            else selections[itemId] = value as V;
        });
    return selections;
}

export interface DropdownCaptureConfig {
    /** Action IDs are `${actionIdPrefix}${itemId}`; the prefix is stripped to recover the id. */
    actionIdPrefix: string;
    /** Option values meaning "no selection" — these clear any prior selection for the item. */
    noneValues: string[];
}

export function captureDropdownSelections(
    body: SlackBody,
    prior: Record<string, string> | undefined,
    config: DropdownCaptureConfig,
): Record<string, string> {
    return captureSelections<{ selected_option?: { value: string } }, string>(
        body,
        prior,
        config.actionIdPrefix,
        (action) => action.selected_option?.value,
        (value) => !value || config.noneValues.includes(value),
    );
}

export interface CheckboxCaptureConfig {
    /** Action IDs are `${actionIdPrefix}${itemId}`; the prefix is stripped to recover the id. */
    actionIdPrefix: string;
}

export function captureCheckboxSelections(
    body: SlackBody,
    prior: Record<string, boolean> | undefined,
    config: CheckboxCaptureConfig,
): Record<string, boolean> {
    return captureSelections<{ selected_options?: unknown[] }, boolean>(
        body,
        prior,
        config.actionIdPrefix,
        (action) =>
            Array.isArray(action.selected_options) && action.selected_options.length > 0
                ? true
                : undefined,
        (value) => value !== true,
    );
}
