/** Block-action / view-state capture key conventions for the waitlist list modal.
 *  The prefixes here are what the capture helpers in shared/slack/modal_state.ts
 *  scan for; rename in lockstep with the helpers. */

export const DROPDOWN_CAPTURE_CONFIG = {
    actionIdPrefix: "action_r",
    noneValues: ["none", "skip"],
};

/** Per-player opt-in checkbox under each dropdown. Unticked by default, so the
 *  default action is "tag only, no email" — admitting tags the customer in
 *  Shopify but only sends the notification email when this box is checked. The
 *  label embeds the player's email and is built per-row in the modal. */
export const CHECKBOX_CAPTURE_CONFIG = {
    actionIdPrefix: "email_r",
};
