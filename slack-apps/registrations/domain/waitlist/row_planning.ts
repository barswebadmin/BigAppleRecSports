/** Build-phase: produce the exact `PreparedRequest`s for every row WITHOUT
 *  sending them. The dry-run preview displays these; the real run executes them.
 *  Builders perform only read/auth lookups (product-by-handle, customer search,
 *  token) needed to make the bytes exact. */

import type { League } from "../league/types.ts";
import type { EmailMessage } from "../../shared/google/email_message.ts";
import type { PreparedRequest } from "../../shared/http/prepared_request.ts";
import { productPageUrl, shopifyCustomerAdminUrl } from "../../config/store.ts";
import { formatProductHandle } from "../league/format.ts";
import { type CustomerTagPlan, planCustomerTag } from "../../legacy/shopify_client/customer_ops.ts";
import { findProductByHandle } from "../../legacy/shopify_client/product_ops.ts";
import type { createShopifyClient } from "../../legacy/shopify_client/client.ts";
import type { getOrCreateGoogleClient } from "../../shared/google/client.ts";
import { buildSendEmailRequest } from "../../shared/google/gmail.ts";
import { buildWaitlistAdmitEmail } from "./admit_email.ts";
import type { ActionResult } from "./action_result.ts";
import { statusText } from "./status_format.ts";
import type { WaitlistEntry } from "./types.ts";

/** Resolved shopify side of an admit: tag plan + the customer admin link to surface. */
export interface AdmitShopifyPlan {
    tagPlan: CustomerTagPlan | null;
    customerAdminUrl?: string;
    /** Notes accumulated for the dry-run preview (product missing, noop, update, create). */
    notes: string[];
}

/** Resolved email side of an admit: built request + the message it encodes. */
export interface AdmitEmailPlan {
    emailRequest: PreparedRequest | null;
    emailMessage: EmailMessage | null;
    /** Skip note for the dry-run preview when the email box was unticked. */
    skipNote?: string;
}

/** Aggregated per-row plan + initial result. Mutated by row_execution.ts during a real run. */
export interface RowProcessing {
    rowStr: string;
    type: "admit" | "remove";
    entry?: WaitlistEntry;
    shouldEmail: boolean;
    result: ActionResult;
    tagPlan: CustomerTagPlan | null;
    emailRequest: PreparedRequest | null;
    emailMessage: EmailMessage | null;
    notes: string[];
    /** Dry-run sheet preview: the row write the downstream step would perform. */
    sheetUrl: string;
    insertedStatus: string;
}

export function initActionResult(args: {
    rowNumber: number;
    type: "admit" | "remove";
    entry: WaitlistEntry | undefined;
    league: League;
}): ActionResult {
    const { rowNumber, type, entry, league } = args;
    return {
        rowNumber,
        type,
        name: `${entry?.firstName ?? ""} ${entry?.lastName ?? ""}`.trim() || `row ${rowNumber}`,
        firstName: entry?.firstName ?? "",
        email: entry?.emailAddress ?? "",
        phone: entry?.phoneNumber,
        league,
        shopifyOk: true,
        emailOk: true,
        emailed: false,
        productUrl: productPageUrl(formatProductHandle(league)),
    };
}

/** Look up the product by handle and plan the customer tag mutation without
 *  sending it. Authors the dry-run note in all four branches (product missing,
 *  noop, update, create) so the preview text stays beside the decision. */
export async function planAdmitShopifyTag(
    shopify: ReturnType<typeof createShopifyClient>,
    entry: WaitlistEntry,
    league: League,
): Promise<AdmitShopifyPlan> {
    const expectedHandle = formatProductHandle(league);
    const product = await findProductByHandle(shopify, expectedHandle);

    if (!product) {
        return {
            tagPlan: null,
            notes: [
                `:warning: Shopify: no product found for handle \`${expectedHandle}\` — check season/year config. No tag will be applied.`,
            ],
        };
    }

    const waitlistTag = `${product.handle}-waitlist`;
    const tagPlan = await planCustomerTag(shopify, entry.emailAddress, waitlistTag, {
        firstName: entry.firstName ?? "",
        lastName: entry.lastName ?? "",
        ...(entry.phoneNumber ? { phone: entry.phoneNumber } : {}),
    });

    const customerAdminUrl = tagPlan.existing?.id
        ? shopifyCustomerAdminUrl(tagPlan.existing.id)
        : undefined;

    let note: string;
    if (tagPlan.action === "noop") {
        note = `Shopify: customer already has \`${waitlistTag}\` — no mutation needed.`;
    } else if (tagPlan.action === "update") {
        note = `Shopify: update existing customer \`${tagPlan.existing?.id}\` → tags become [${
            tagPlan.finalTags.join(", ")
        }].`;
    } else {
        note =
            `Shopify: no customer for ${entry.emailAddress} → create with tag \`${waitlistTag}\`.`;
    }

    return { tagPlan, customerAdminUrl, notes: [note] };
}

/** Build the gmail send request (or a skip note when the email box was unticked). */
export async function planAdmitEmail(
    google: ReturnType<typeof getOrCreateGoogleClient>,
    entry: WaitlistEntry,
    shouldEmail: boolean,
    league: League,
): Promise<AdmitEmailPlan> {
    if (!shouldEmail) {
        return {
            emailRequest: null,
            emailMessage: null,
            skipNote: "Email: box unticked → no email will be sent (tag only).",
        };
    }
    if (!entry.emailAddress) return { emailRequest: null, emailMessage: null };

    const emailMessage = buildWaitlistAdmitEmail(
        { firstName: entry.firstName, emailAddress: entry.emailAddress },
        league,
    );
    const emailRequest = await buildSendEmailRequest(google, emailMessage);
    return { emailRequest, emailMessage };
}

/** Compose a full `RowProcessing` from the row's selection + the sheet entry.
 *  Orchestrator only — the actual planning lives in `planAdmitShopifyTag` and
 *  `planAdmitEmail`. Removes (`type === "remove"`) skip planning entirely; the
 *  sheet step downstream is the only side effect a remove produces. */
export async function buildRowProcessing(args: {
    rowStr: string;
    type: "admit" | "remove";
    entry?: WaitlistEntry;
    shouldEmail: boolean;
    shopify: ReturnType<typeof createShopifyClient>;
    google: ReturnType<typeof getOrCreateGoogleClient>;
    /** Used for display only when the row can't be resolved to a sheet entry. */
    fallbackLeague: League;
    timestamp: string;
    sheetUrl: string;
}): Promise<RowProcessing> {
    const { rowStr, type, entry, shouldEmail, shopify, google, fallbackLeague } = args;
    const rowNumber = Number(rowStr);
    // Entry already carries its full League (populated by sheet_parser); fall back
    // to the modal-selected league only when the row no longer resolves to an entry.
    const league: League = entry?.league ?? fallbackLeague;
    const result = initActionResult({ rowNumber, type, entry, league });

    let tagPlan: CustomerTagPlan | null = null;
    let emailRequest: PreparedRequest | null = null;
    let emailMessage: EmailMessage | null = null;
    const notes: string[] = [];

    if (entry && type === "admit") {
        const shopifyPlan = await planAdmitShopifyTag(shopify, entry, league);
        tagPlan = shopifyPlan.tagPlan;
        if (shopifyPlan.customerAdminUrl) result.customerAdminUrl = shopifyPlan.customerAdminUrl;
        notes.push(...shopifyPlan.notes);

        const emailPlan = await planAdmitEmail(google, entry, shouldEmail, league);
        emailRequest = emailPlan.emailRequest;
        emailMessage = emailPlan.emailMessage;
        if (emailPlan.skipNote) notes.push(emailPlan.skipNote);
    }

    return {
        rowStr,
        type,
        entry,
        shouldEmail,
        result,
        tagPlan,
        emailRequest,
        emailMessage,
        notes,
        sheetUrl: args.sheetUrl,
        insertedStatus: statusText(type, args.timestamp),
    };
}
