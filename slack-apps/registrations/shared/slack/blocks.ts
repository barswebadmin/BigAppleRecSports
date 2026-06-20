export type Block = Record<string, unknown>;

// ── Atoms ──────────────────────────────────────────────────────────────────

export function plainText(text: string, emoji = false) {
    return {
        type: "plain_text" as const,
        text,
        ...(emoji ? { emoji: true } : {}),
    };
}

/** Two-line mrkdwn field with a blank line above the label, used in the `fields`
 *  array of two-column section blocks so rows breathe instead of stacking tight. */
export function mrkdwnField(label: string, value: string): Block {
    return { type: "mrkdwn", text: `\n*${label}*\n${value}` };
}

// ── Layout blocks ──────────────────────────────────────────────────────────

export function section(text: string): Block {
    return { type: "section", text: { type: "mrkdwn", text } };
}

export function header(text: string): Block {
    return {
        type: "header",
        text: { type: "plain_text", text: text.slice(0, 150), emoji: true },
    };
}

export function divider(): Block {
    return { type: "divider" };
}

export function context(text: string): Block {
    return {
        type: "context",
        elements: [{ type: "mrkdwn", text }],
    };
}

/** Shape needed to render a validation outcome in Block Kit (any domain). */
export type ValidationSummarySource = {
    validation_passed: boolean;
    warnings: string[];
};

/** Green check when passed with no warnings; otherwise a warning count header and one section per bullet. */
export function validationSummaryBlocks(v: ValidationSummarySource): Block[] {
    if (v.validation_passed && v.warnings.length === 0) {
        return [section(":white_check_mark: *Validation passed* — no warnings")];
    }
    const plural = v.warnings.length === 1 ? "" : "s";
    return [
        section(`:warning: *${v.warnings.length} warning${plural}*`),
        ...v.warnings.map((w) => section(`• ${w}`)),
    ];
}

// ── Interactive element options ────────────────────────────────────────────

export interface Option {
    text: { type: "plain_text"; text: string };
    value: string;
}

export function toOption({ label, value }: { label: string; value: string }): Option {
    return { text: plainText(label), value };
}

export function toOptions(items: { label: string; value: string }[]): Option[] {
    return items.map(toOption);
}

// ── Input / actions wrappers ───────────────────────────────────────────────

export function input(args: {
    blockId: string;
    label: string;
    element: Block;
    optional?: boolean;
    /** Fire a block-actions event on every value change (used to re-render the
     *  modal in place when a select drives downstream defaults). */
    dispatchAction?: boolean;
    /** Optional helper text below the input (Block Kit `hint`). */
    hint?: string;
}): Block {
    return {
        type: "input",
        block_id: args.blockId,
        label: plainText(args.label),
        element: args.element,
        ...(args.optional ? { optional: true } : {}),
        ...(args.dispatchAction ? { dispatch_action: true } : {}),
        ...(args.hint ? { hint: plainText(args.hint) } : {}),
    };
}

// ── Interactive elements ───────────────────────────────────────────────────

export function staticSelect(args: {
    actionId: string;
    placeholder: string;
    options: Option[];
    initial?: Option;
}): Block {
    return {
        type: "static_select",
        action_id: args.actionId,
        placeholder: plainText(args.placeholder),
        options: args.options,
        ...(args.initial ? { initial_option: args.initial } : {}),
    };
}

export function radioButtons(args: {
    actionId: string;
    options: Option[];
    initial?: Option;
}): Block {
    return {
        type: "radio_buttons",
        action_id: args.actionId,
        options: args.options,
        ...(args.initial ? { initial_option: args.initial } : {}),
    };
}

export function checkboxes(args: {
    actionId: string;
    options: Option[];
    initial?: Option[];
}): Block {
    return {
        type: "checkboxes",
        action_id: args.actionId,
        options: args.options,
        ...(args.initial?.length ? { initial_options: args.initial } : {}),
    };
}
