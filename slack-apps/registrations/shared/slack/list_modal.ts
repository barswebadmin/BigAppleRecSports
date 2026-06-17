/**
 * Generic paginated list modal with a per-item action dropdown.
 * No domain imports — all behavior is dictated by ListModalConfig params.
 */

import { type Block, context, divider, header, plainText, section } from "./blocks.ts";

export interface ActionOption {
    label: string;
    value: string;
}

export interface ListModalConfig<T> {
    callbackId: string;
    title: string;
    submitLabel?: string;
    closeLabel?: string;
    /** Optional large bold heading line (renders emoji shortcodes). */
    headerText?: string;
    /** Optional smaller line beneath the header (e.g. full league + division). */
    subText?: string;
    /** Optional smaller instruction paragraph (rendered as a context block). */
    instructionText?: string;
    /** Full item list; the modal slices the current page from offset/pageSize. */
    items: T[];
    offset: number;
    pageSize: number;
    /** Bold name/title line shown in the item's section (alongside the dropdown). */
    formatItemTitle: (item: T) => string;
    /** Optional small lines rendered as a context block beneath the item. */
    formatItemContextLines?: (item: T) => string[];
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
    /** Label used for read-only items. Defaults to formatItemTitle. */
    formatReadOnlyLabel?: (item: T) => string;
    /** Optional single checkbox rendered beneath each item's dropdown (e.g. "also email"). */
    checkbox?: {
        getBlockId: (item: T) => string;
        getActionId: (item: T) => string;
        /** Per-item checkbox option (e.g. label that embeds the player's email). */
        getOption: (item: T) => ActionOption;
        /** Map of item id → checked, used to preserve ticks across pagination. */
        existingSelections?: Record<string, boolean>;
        /** Return false to omit the checkbox for an item. Defaults to always show. */
        shouldShow?: (item: T) => boolean;
    };
}

function toSelectOption(opt: ActionOption) {
    return { text: plainText(opt.label), value: opt.value };
}

/** Text/emoji content for the modal's header region. */
interface ModalHeaderConfig {
    headerText?: string;
    subText?: string;
    instructionText?: string;
}

/**
 * Reusable modal-header component: an optional big-bold `header` line (the
 * strongest native "stand out" treatment), an optional smaller sub-line, then
 * the instruction copy, separated by dividers. Composed by buildListModal so
 * every caller (dry-run and real-run) renders the header the same way; only the
 * text differs.
 *
 * Note on Slack limits: modal text can't be colored, underlined, boxed, or
 * resized. `header` blocks render big/bold; `context` blocks render small/gray.
 */
function buildModalHeaderBlocks(config: ModalHeaderConfig): Block[] {
    const blocks: Block[] = [];

    if (config.headerText) {
        blocks.push(header(config.headerText));
    }
    if (config.subText) blocks.push(context(config.subText));
    if (config.headerText || config.subText) blocks.push(divider());
    if (config.instructionText) blocks.push(context(config.instructionText));
    blocks.push(divider());
    return blocks;
}

/** Either the read-only label or the interactive dropdown (+ optional context
 *  lines + optional checkbox) for a single page item — flat per-item pipeline,
 *  no nested loops in `buildListModal`. */
function itemToBlocks<T>(item: T, config: ListModalConfig<T>): Block[] {
    const showDropdown = config.shouldShowDropdown?.(item) ?? true;
    if (!showDropdown) {
        return [section((config.formatReadOnlyLabel ?? config.formatItemTitle)(item))];
    }
    const id = String(config.getItemId(item));
    const options = config.actionOptions.map(toSelectOption);
    const selected = config.existingSelections?.[id];
    const initialOption = selected ? options.find((o) => o.value === selected) : undefined;
    const contextLines = config.formatItemContextLines?.(item) ?? [];

    return [
        {
            type: "section",
            block_id: config.getBlockId(item),
            text: { type: "mrkdwn", text: config.formatItemTitle(item) },
            accessory: {
                type: "static_select",
                action_id: config.getActionId(item),
                placeholder: plainText("Choose..."),
                options,
                ...(initialOption ? { initial_option: initialOption } : {}),
            },
        },
        ...(contextLines.length > 0 ? [context(contextLines.join("\n"))] : []),
        ...checkboxBlocks(item, id, config.checkbox),
    ];
}

function checkboxBlocks<T>(
    item: T,
    id: string,
    checkbox: ListModalConfig<T>["checkbox"],
): Block[] {
    if (!checkbox || !(checkbox.shouldShow?.(item) ?? true)) return [];
    const opt = checkbox.getOption(item);
    const cbOption = { text: plainText(opt.label), value: opt.value };
    const checked = checkbox.existingSelections?.[id] === true;
    return [{
        type: "actions",
        block_id: checkbox.getBlockId(item),
        elements: [{
            type: "checkboxes",
            action_id: checkbox.getActionId(item),
            options: [cbOption],
            ...(checked ? { initial_options: [cbOption] } : {}),
        }],
    }];
}

function paginationBlocks<T>(config: ListModalConfig<T>): Block[] {
    const buttons: Block[] = [];
    if (config.offset > 0) {
        buttons.push({
            type: "button",
            text: plainText("← Back"),
            action_id: config.paginationActionIds.prev,
        });
    }
    if (config.offset + config.pageSize < config.items.length) {
        buttons.push({
            type: "button",
            text: plainText("Next →"),
            action_id: config.paginationActionIds.next,
        });
    }
    return buttons.length > 0 ? [{ type: "actions", elements: buttons }] : [];
}

export function buildListModal<T>(config: ListModalConfig<T>): Record<string, unknown> {
    const page = config.items.slice(config.offset, config.offset + config.pageSize);
    const bodyBlocks: Block[] = config.items.length === 0 ? [section(config.emptyMessage)] : [
        ...buildModalHeaderBlocks({
            headerText: config.headerText,
            subText: config.subText,
            instructionText: config.instructionText,
        }),
        ...page.flatMap((item) => itemToBlocks(item, config)),
        ...paginationBlocks(config),
    ];

    return {
        type: "modal",
        callback_id: config.callbackId,
        title: plainText(config.title),
        ...(config.submitLabel ? { submit: plainText(config.submitLabel) } : {}),
        ...(config.closeLabel ? { close: plainText(config.closeLabel) } : {}),
        blocks: bodyBlocks,
        ...(config.metadata ? { private_metadata: config.metadata } : {}),
        notify_on_close: true,
    };
}
