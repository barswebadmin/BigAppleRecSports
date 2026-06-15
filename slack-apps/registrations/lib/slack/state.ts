/**
 * Modal private_metadata state helpers — generic over state shape.
 */

// deno-lint-ignore no-explicit-any
export function extractModalState<S>(body: any): S {
    return JSON.parse(body.view?.private_metadata || "{}");
}

export interface DropdownCaptureConfig {
    /** Action IDs are `${actionIdPrefix}${itemId}`; the prefix is stripped to recover the id. */
    actionIdPrefix: string;
    /** Option values meaning "no selection" — these clear any prior selection for the item. */
    noneValues: string[];
}

/**
 * Merge the visible page's dropdown selections into a persistent selections
 * map (`state[selectionsKey]`). view.state only holds values for currently
 * rendered blocks, so this must run before every pagination and on submit to
 * retain selections made across pages.
 */
export function captureDropdownSelections(
    // deno-lint-ignore no-explicit-any
    body: any,
    state: Record<string, unknown>,
    selectionsKey: string,
    config: DropdownCaptureConfig,
): void {
    const selections = (state[selectionsKey] ?? {}) as Record<string, string>;
    const values = body.view?.state?.values ?? {};

    for (const block of Object.values(values)) {
        for (
            const [actionId, action] of Object.entries(
                block as Record<string, { selected_option?: { value: string } }>,
            )
        ) {
            if (!actionId.startsWith(config.actionIdPrefix)) continue;
            const itemId = actionId.slice(config.actionIdPrefix.length);
            const value = action.selected_option?.value;
            if (!value || config.noneValues.includes(value)) {
                delete selections[itemId];
            } else {
                selections[itemId] = value;
            }
        }
    }

    state[selectionsKey] = selections;
}

export interface CheckboxCaptureConfig {
    /** Action IDs are `${actionIdPrefix}${itemId}`; the prefix is stripped to recover the id. */
    actionIdPrefix: string;
}

/**
 * Merge the visible page's checkbox ticks into a persistent map
 * (`state[selectionsKey]`: itemId → true). Like captureDropdownSelections,
 * view.state only holds currently rendered blocks, so this must run before
 * every pagination and on submit to retain ticks made across pages. A box with
 * no selected options clears any prior tick for that item.
 */
export function captureCheckboxSelections(
    // deno-lint-ignore no-explicit-any
    body: any,
    state: Record<string, unknown>,
    selectionsKey: string,
    config: CheckboxCaptureConfig,
): void {
    const selections = (state[selectionsKey] ?? {}) as Record<string, boolean>;
    const values = body.view?.state?.values ?? {};

    for (const block of Object.values(values)) {
        for (
            const [actionId, action] of Object.entries(
                block as Record<string, { selected_options?: unknown[] }>,
            )
        ) {
            if (!actionId.startsWith(config.actionIdPrefix)) continue;
            const itemId = actionId.slice(config.actionIdPrefix.length);
            const checked = Array.isArray(action.selected_options) &&
                action.selected_options.length > 0;
            if (checked) selections[itemId] = true;
            else delete selections[itemId];
        }
    }

    state[selectionsKey] = selections;
}
