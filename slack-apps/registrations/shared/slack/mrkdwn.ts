/** Slack mrkdwn helpers — hyperlinks, user mentions, and shared link copy. */

/** Default hyperlink display text reused across workflows. Keep link copy here
 *  so it stays consistent everywhere (and the emoji is changed in one place). */
export const SLACK_LINK_TEXT = {
    googleSheets: ":paperclip: Open in Google Sheets",
    shopifyCustomer: "Shopify profile",
    productPage: "product page",
} as const;

/** kwargs accepted by `hyperlink` / `tagUser`. The `formatting` field is reserved
 *  for future bold/italic/color knobs and is currently a no-op; consumers may
 *  pass `{ formatting: { … } }` defensively without breaking when knobs land. */
export interface MrkdwnOptions {
    formatting?: Record<string, unknown> | null;
}

/** Slack mrkdwn hyperlink: `<url|text>`. */
// deno-lint-ignore no-unused-vars
export function hyperlink(text: string, url: string, options: MrkdwnOptions = {}): string {
    return `<${url}|${text}>`;
}

/** Mention a Slack user, optionally with a label prefix (e.g. `"Processed by"`).
 *  Default prefix is empty so the helper stays reusable across labels. */
// deno-lint-ignore no-unused-vars
export function tagUser(userId: string, prefix = "", options: MrkdwnOptions = {}): string {
    const mention = `<@${userId}>`;
    return prefix ? `${prefix} ${mention}` : mention;
}
