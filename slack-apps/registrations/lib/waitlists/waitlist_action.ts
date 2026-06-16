/**
 * Wire contract for `actions_json` passed between waitlist workflow steps
 * (resolve → update sheet; handle → update sheet).
 */
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
