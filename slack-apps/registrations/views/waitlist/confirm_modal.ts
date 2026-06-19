/** Confirmation modal pushed when the reviewer clicks Submit on the list
 *  modal. Same downstream logic runs whether dry-run or real — only the title
 *  and an italicized context note differ. */

import { type Block, context, section } from "../../shared/slack/blocks.ts";
import { modal, type ViewBuilder } from "../../shared/slack/message.ts";

/** Input shape for the confirmation modal. */
export interface WaitlistConfirmModal {
    callbackId: string;
    admitNames: string[];
    removeNames: string[];
    dry: boolean;
    metadata: string;
}

const HEADER_TEXT = "*Please confirm these changes:*";
const ADMIT_GROUP_LABEL = "Admit";
const REMOVE_GROUP_LABEL = "Remove";
const TITLE_NORMAL = "Confirm changes";
const TITLE_DRY = "Confirm (DRY RUN)";
const SUBMIT_LABEL = "Confirm";
const CLOSE_LABEL = "Cancel";
const DRY_CONTEXT_NOTE =
    ":test_tube: *DRY RUN* — nothing will be sent. Submitting posts a preview of the exact requests.";

// ============================================================================

// ============================================================================

/** Section listing a labelled group of names; `null` when the group is empty
 *  so the caller can filter it out without a conditional in the block list. */
function groupSection(label: string, names: string[]): Block | null {
    if (names.length === 0) return null;
    const bullets = names.map((n) => `•  ${n}`).join("\n");
    return section(`*${label}* (${names.length})\n${bullets}`);
}

export const buildWaitlistConfirmModal: ViewBuilder<WaitlistConfirmModal> = (input) => {
    const blocks: Block[] = [
        section(HEADER_TEXT),
        groupSection(ADMIT_GROUP_LABEL, input.admitNames),
        groupSection(REMOVE_GROUP_LABEL, input.removeNames),
        input.dry ? context(DRY_CONTEXT_NOTE) : null,
    ].filter((b): b is Block => b !== null);

    return modal({
        callbackId: input.callbackId,
        title: input.dry ? TITLE_DRY : TITLE_NORMAL,
        submitLabel: SUBMIT_LABEL,
        closeLabel: CLOSE_LABEL,
        blocks,
        metadata: input.metadata,
    });
};
