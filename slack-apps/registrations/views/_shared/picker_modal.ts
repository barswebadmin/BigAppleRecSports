/**
 * Generic single-select picker modal (paginated radio button list + optional
 * extra input blocks). Refund-agnostic — every id it emits is derived from
 * the caller's `callbackId` argument so the same builder serves any flow that
 * needs "operator picks one row from a list".
 *
 * Implementation note (per Stage 1 design.md instruction):
 * `slack-apps/registrations/shared/slack/list_modal.ts` already exists, but it
 * implements a fundamentally different pattern — one independent dropdown +
 * optional checkbox per row, with selections accumulated across pagination.
 * The picker modal needs a single radio group whose selection is mutually
 * exclusive across all paginated rows, plus a different action-id contract
 * (D29: `${callbackId}__radio_<page>`, `${callbackId}__next_page`,
 * `${callbackId}__prev_page`). Re-using `list_modal.ts` would have required
 * folding two distinct interaction models into one config object, so this
 * file is built as a sibling that calls into the same low-level
 * `shared/slack/blocks.ts` / `shared/slack/message.ts` primitives.
 */

import { type Block, divider, plainText, section } from "../../shared/slack/blocks.ts";
import { modal, type SlackView } from "../../shared/slack/message.ts";

/** Default page size for the picker — caller can override via `pageSize`. */
export const PICKER_ENTRIES_PER_PAGE_DEFAULT = 10;

/** Action ids the picker emits, derived from the caller's `callbackId`. The
 *  radio prefix is appended with the page index at use-site (radios on
 *  different pages must have distinct `action_id`s so Slack's view-state
 *  capture treats them as independent inputs). */
export function pickerActionIds(callbackId: string): {
    radioPrefix: string;
    nextPage: string;
    prevPage: string;
} {
    return {
        radioPrefix: `${callbackId}__radio_`, // page index appended at use site
        nextPage: `${callbackId}__next_page`,
        prevPage: `${callbackId}__prev_page`,
    };
}

export interface PickerFormattedItem {
    /** Bold/title-line copy (rendered as the radio option's label). */
    title: string;
    /** Optional supplementary lines rendered as a small context block under the option. */
    context?: string[];
}

export interface PickerModalArgs<T> {
    callbackId: string;
    title: string;
    submitLabel: string;
    closeLabel: string;
    items: T[];
    formatItem: (item: T) => PickerFormattedItem;
    getItemId: (item: T) => string | number;
    /** Default `PICKER_ENTRIES_PER_PAGE_DEFAULT` (= 10). */
    pageSize?: number;
    /** 0-based offset into `items` (drives Back/Next pagination math). */
    currentOffset?: number;
    /** Round-trip the operator's selection across `views.update`. */
    selectedItemId?: string | number | null;
    /** Block list rendered between the picker and the pagination row — the
     *  refund flow uses this for the test-mode toggle and "post to channel"
     *  override field. The picker has no opinion about what's inside. */
    extraInputBlocks?: Block[];
    /** Serialized into `private_metadata` (so callers can round-trip arbitrary state). */
    metadata?: Record<string, unknown>;
    /** Optional empty-list copy. Default: "No items to pick from." */
    emptyMessage?: string;
}

function radioOptions<T>(
    pageItems: T[],
    args: PickerModalArgs<T>,
): {
    value: string;
    text: { type: "plain_text"; text: string };
    description?: { type: "mrkdwn"; text: string };
}[] {
    return pageItems.map((item) => {
        const formatted = args.formatItem(item);
        const id = String(args.getItemId(item));
        const titleText = formatted.title.length > 75
            ? `${formatted.title.slice(0, 72)}…`
            : formatted.title;
        const opt: {
            value: string;
            text: { type: "plain_text"; text: string };
            description?: { type: "mrkdwn"; text: string };
        } = {
            value: id,
            text: plainText(titleText) as { type: "plain_text"; text: string },
        };
        if (formatted.context && formatted.context.length > 0) {
            const ctxText = formatted.context.join(" • ");
            const trimmed = ctxText.length > 75 ? `${ctxText.slice(0, 72)}…` : ctxText;
            opt.description = { type: "mrkdwn", text: trimmed };
        }
        return opt;
    });
}

function paginationBlocks<T>(
    args: PickerModalArgs<T>,
    offset: number,
    pageSize: number,
): Block[] {
    const ids = pickerActionIds(args.callbackId);
    const buttons: Block[] = [];
    if (offset > 0) {
        buttons.push({
            type: "button",
            text: plainText("← Back"),
            action_id: ids.prevPage,
        });
    }
    if (offset + pageSize < args.items.length) {
        buttons.push({
            type: "button",
            text: plainText("Next →"),
            action_id: ids.nextPage,
        });
    }
    return buttons.length > 0 ? [{ type: "actions", elements: buttons }] : [];
}

/**
 * Build a single-select picker modal view. Returns a `SlackView` ready to
 * splat into `client.views.open` / `client.views.update`.
 */
export function pickerModal<T>(args: PickerModalArgs<T>): SlackView {
    const pageSize = args.pageSize ?? PICKER_ENTRIES_PER_PAGE_DEFAULT;
    const offset = args.currentOffset ?? 0;
    const pageItems = args.items.slice(offset, offset + pageSize);
    const ids = pickerActionIds(args.callbackId);
    const pageIndex = pageSize > 0 ? Math.floor(offset / pageSize) : 0;
    const radioActionId = `${ids.radioPrefix}${pageIndex}`;

    const blocks: Block[] = [];

    if (args.items.length === 0) {
        blocks.push(section(args.emptyMessage ?? "No items to pick from."));
    } else {
        const options = radioOptions(pageItems, args);
        const selectedId = args.selectedItemId !== null && args.selectedItemId !== undefined
            ? String(args.selectedItemId)
            : null;
        const initialOption = selectedId ? options.find((o) => o.value === selectedId) : undefined;

        blocks.push({
            type: "input",
            block_id: `${args.callbackId}__picker_block_${pageIndex}`,
            label: plainText("Select one"),
            element: {
                type: "radio_buttons",
                action_id: radioActionId,
                options,
                ...(initialOption ? { initial_option: initialOption } : {}),
            },
        });
        const paginationRow = paginationBlocks(args, offset, pageSize);
        if (paginationRow.length > 0) {
            blocks.push(...paginationRow);
        }
    }

    if (args.extraInputBlocks && args.extraInputBlocks.length > 0) {
        blocks.push(divider());
        blocks.push(...args.extraInputBlocks);
    }

    return modal({
        callbackId: args.callbackId,
        title: args.title,
        submitLabel: args.submitLabel,
        closeLabel: args.closeLabel,
        blocks,
        metadata: args.metadata ? JSON.stringify(args.metadata) : undefined,
        notifyOnClose: true,
    });
}
