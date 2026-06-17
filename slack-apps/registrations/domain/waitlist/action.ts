/** Wire contract for `actions_json` passed between waitlist workflow steps
 *  (resolve → update sheet; handle → update sheet). */

import type { League } from "../league/types.ts";
import type { RowProcessing } from "./row_planning.ts";

export interface WaitlistAction {
    type: "admit" | "remove" | "order";
    rowNumber: string;
    firstName: string;
    lastName?: string;
    emailAddress: string;
    sport?: string;
    day?: string;
    division?: string;
}

/** Project planned/executed `RowProcessing` rows into the wire-format actions
 *  payload consumed by the downstream `update_waitlist_spreadsheet` step. */
export function toWaitlistActions(
    processed: RowProcessing[],
    fallbackLeague: League,
): WaitlistAction[] {
    return processed.map((p) => {
        const lg = p.result.league ?? fallbackLeague;
        return {
            type: p.result.type,
            rowNumber: String(p.result.rowNumber),
            firstName: p.result.firstName,
            lastName: p.entry?.lastName ?? "",
            emailAddress: p.result.email,
            sport: lg.sport,
            day: lg.day,
            division: lg.division,
        };
    });
}
