/**
 * Generic paginated list modal with a per-item action dropdown.
 * No domain imports — all behavior is dictated by ListModalConfig params.
 */

export interface RichTextElement {
    text: string;
    style?: { bold?: boolean; italic?: boolean };
}

export interface ActionOption {
    label: string;
    value: string;
}

export interface ListModalConfig<T> {
    callbackId: string;
    title: string;
    submitLabel?: string;
    headerText: string;
    summaryElements?: RichTextElement[];
    instructionText?: string;
    /** Full item list; the modal slices the current page from offset/pageSize. */
    items: T[];
    offset: number;
    pageSize: number;
    formatItemLabel: (item: T) => string;
    getItemId: (item: T) => string | number;
    getBlockId: (item: T) => string;
    getActionId: (item: T) => string;
    actionOptions: ActionOption[];
    paginationActionIds: { prev: string; next: string };
    /** Map of item id → previously selected option value, used to preselect dropdowns. */
    existingSelections?: Record<string, string>;
    /** Serialized state stored in private_metadata. */
    metadata?: string;
    emptyMessage: string;
    /** Return false to render the item read-only (no dropdown). Defaults to always show. */
    shouldShowDropdown?: (item: T) => boolean;
    /** Label used for read-only items. Defaults to formatItemLabel. */
    formatReadOnlyLabel?: (item: T) => string;
}

type Block = Record<string, unknown>;

const plainText = (text: string) => ({ type: "plain_text" as const, text });
const mrkdwnSection = (text: string): Block => ({
    type: "section",
    text: { type: "mrkdwn", text },
});

function toSelectOption(opt: ActionOption) {
    return { text: plainText(opt.label), value: opt.value };
}

export function buildListModal<T>(config: ListModalConfig<T>): Record<string, unknown> {
    const blocks: Block[] = [];

    blocks.push({ type: "header", text: plainText(config.headerText) });

    if (config.summaryElements?.length) {
        blocks.push({
            type: "rich_text",
            elements: [
                {
                    type: "rich_text_section",
                    elements: config.summaryElements.map((e) => ({
                        type: "text",
                        text: e.text,
                        ...(e.style ? { style: e.style } : {}),
                    })),
                },
            ],
        });
    }

    if (config.instructionText) blocks.push(mrkdwnSection(config.instructionText));
    blocks.push({ type: "divider" });

    if (config.items.length === 0) {
        blocks.push(mrkdwnSection(config.emptyMessage));
    } else {
        const page = config.items.slice(config.offset, config.offset + config.pageSize);
        for (const item of page) {
            const showDropdown = config.shouldShowDropdown?.(item) ?? true;
            if (!showDropdown) {
                blocks.push(
                    mrkdwnSection((config.formatReadOnlyLabel ?? config.formatItemLabel)(item)),
                );
                continue;
            }

            const id = String(config.getItemId(item));
            const selected = config.existingSelections?.[id];
            const options = config.actionOptions.map(toSelectOption);
            const initialOption = selected ? options.find((o) => o.value === selected) : undefined;

            blocks.push({
                type: "section",
                block_id: config.getBlockId(item),
                text: { type: "mrkdwn", text: config.formatItemLabel(item) },
                accessory: {
                    type: "static_select",
                    action_id: config.getActionId(item),
                    placeholder: plainText("Choose..."),
                    options,
                    ...(initialOption ? { initial_option: initialOption } : {}),
                },
            });
        }

        const buttons: Block[] = [];
        if (config.offset > 0) {
            buttons.push({
                type: "button",
                text: plainText(`← Prev ${config.pageSize}`),
                action_id: config.paginationActionIds.prev,
            });
        }
        if (config.offset + config.pageSize < config.items.length) {
            buttons.push({
                type: "button",
                text: plainText(`Next ${config.pageSize} →`),
                action_id: config.paginationActionIds.next,
            });
        }
        if (buttons.length > 0) blocks.push({ type: "actions", elements: buttons });
    }

    return {
        type: "modal",
        callback_id: config.callbackId,
        title: plainText(config.title),
        ...(config.submitLabel ? { submit: plainText(config.submitLabel) } : {}),
        blocks,
        ...(config.metadata ? { private_metadata: config.metadata } : {}),
        notify_on_close: true,
    };
}
