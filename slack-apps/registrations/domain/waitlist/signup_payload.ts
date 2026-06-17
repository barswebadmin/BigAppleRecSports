/**
 * Wire contract for the `receive_waitlist_order` webhook body.
 * Producers POST JSON with snake_case field names.
 */
export interface WaitlistSignupPayload {
    email: string;
    sport: string;
    day: string;
    division: string;
    order_number?: string;
}
