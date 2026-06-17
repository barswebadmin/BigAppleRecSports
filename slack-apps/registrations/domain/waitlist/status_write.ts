/** Persist Status-column writes for a batch of admitted/removed waitlist rows.
 *  The Status column is resolved by `fetchWaitlists` in the same round-trip
 *  that returns the waitlist rows, so writers never need a second metadata
 *  call. */

import { columnToLetter, getOrCreateGoogleClient } from "../../shared/google/client.ts";
import type { WaitlistAction } from "./action.ts";
import { fetchWaitlists, WAITLIST_SPREADSHEET_ID, WAITLIST_TAB } from "./sheet.ts";
import { formatStatusTimestamp, statusText } from "./status_format.ts";

/** Write Status cells for each action. No-ops on empty input. Errors are
 *  logged, not raised — the workflow proceeds either way and the cell stays
 *  blank for manual followup. */
export async function applyStatusWrites(
    env: Record<string, string>,
    actions: WaitlistAction[],
): Promise<void> {
    if (actions.length === 0) return;
    try {
        const google = getOrCreateGoogleClient(env);
        const timestamp = formatStatusTimestamp();
        const { statusColumnIndex: statusCol } = await fetchWaitlists(env);

        const writes = actions.map((action) => ({
            action,
            update: {
                row: Number(action.rowNumber),
                col: statusCol,
                value: statusText(action.type, timestamp),
            },
        }));
        await google.updateCells(
            WAITLIST_SPREADSHEET_ID,
            WAITLIST_TAB.name,
            writes.map((w) => w.update),
        );

        writes.forEach(({ action, update }) =>
            console.log(
                `[update_sheet] ${
                    columnToLetter(statusCol)
                }${action.rowNumber}: "${update.value}" (${action.firstName} ${action.emailAddress})`,
            )
        );
    } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error(`[update_sheet] ${msg}`);
    }
}
