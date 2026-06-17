/** Slack UI defaults: link copy, mrkdwn helpers, list-modal options, gmail sender. */

import { ORG_DOMAIN } from "./store.ts";

/**
 * Default hyperlink display text reused across workflows. Keep link copy here
 * so it stays consistent everywhere (and the emoji is changed in one place).
 */
export const SLACK_LINK_TEXT = {
    googleSheets: ":paperclip: Open in Google Sheets",
    shopifyCustomer: "Shopify profile",
    productPage: "product page",
} as const;

/** Slack mrkdwn hyperlink: `<url|text>`. */
export function slackLink(text: string, url: string): string {
    return `<${url}|${text}>`;
}

/** Mention a Slack member with a leading label, e.g. `Processed by <@U123>`. */
export function tagSlackMember(userId: string, prefix = "Processed by"): string {
    return `${prefix} <@${userId}>`;
}

// ── Waitlist list-modal options ─────────────────────────────────────

export const ENTRIES_PER_PAGE = 3;
export const SHEET_STATUS_FORMAT = "M/d 'at' h:mm aaa";

export const ACTION_OPTIONS = [
    { label: "No changes", value: "none" },
    { label: "Admit", value: "admit" },
    { label: "Remove", value: "remove" },
];

// ── Gmail ───────────────────────────────────────────────────────────

export const DEFAULT_GMAIL_SENDER = {
    name: "Big Apple Rec Sports",
    email_address: `web@${ORG_DOMAIN}`,
};
