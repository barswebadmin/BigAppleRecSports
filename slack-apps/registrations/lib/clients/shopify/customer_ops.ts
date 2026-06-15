/**
 * Shopify customer operations — focused, composable functions.
 *
 * The waitlist-tag operation is split into a builder (`planCustomerTag`: does
 * the read to decide create vs. update and the final tag set, then BUILDS the
 * mutation) and an executor (`executeCustomerTag`: sends it). Dry-run uses the
 * builder only, so it can show the exact mutation that would be sent.
 */

import type { PreparedRequest } from "../prepared_request.ts";
import type { ShopifyClient } from "./client.ts";
import {
    CUSTOMER_CREATE_MUTATION,
    CUSTOMER_SEARCH_QUERY,
    CUSTOMER_UPDATE_MUTATION,
} from "./types/customers.ts";
import type {
    CreateCustomerInput,
    CustomerCreateResponse,
    CustomerOpResult,
    CustomerSearchResponse,
    CustomerUpdateResponse,
    ShopifyCustomer,
} from "./types/customers.ts";

const log = (fn: string, ...args: unknown[]) => console.log(`[shopify:${fn}]`, ...args);

function addTagIfMissing(existingTags: string[], newTag: string): string[] {
    if (existingTags.includes(newTag)) return existingTags;
    return [...existingTags, newTag];
}

export async function findCustomerByEmail(
    client: ShopifyClient,
    email: string,
): Promise<ShopifyCustomer | null> {
    const { data, errors } = await client.gql<CustomerSearchResponse>(CUSTOMER_SEARCH_QUERY, {
        query: `email:${email}`,
    });
    if (errors.length > 0 || !data) return null;
    const customer = data.customers.nodes[0] ?? null;
    log("findCustomerByEmail", `${email} → ${customer ? customer.id : "not found"}`);
    return customer;
}

/**
 * The mutation that will reconcile a customer's waitlist tag:
 *  - `update`: customer exists and is missing the tag → customerUpdate with merged tags
 *  - `create`: no customer for the email → customerCreate with the tag
 *  - `noop`:   customer exists and already has the tag → no request needed
 */
export interface CustomerTagPlan {
    action: "create" | "update" | "noop";
    existing: ShopifyCustomer | null;
    finalTags: string[];
    /** The mutation to send, or null when action is "noop". */
    request: PreparedRequest | null;
}

/**
 * Resolve (via a read) whether the tag op is a create/update/noop and BUILD the
 * mutation without sending it. Performs only the customer-search read.
 */
export async function planCustomerTag(
    client: ShopifyClient,
    email: string,
    tag: string,
    createInput?: Omit<CreateCustomerInput, "email" | "tags">,
): Promise<CustomerTagPlan> {
    const existing = await findCustomerByEmail(client, email);

    if (existing) {
        if (existing.tags.includes(tag)) {
            return { action: "noop", existing, finalTags: existing.tags, request: null };
        }
        const finalTags = addTagIfMissing(existing.tags, tag);
        const request = client.buildGqlRequest(
            `Shopify customerUpdate — add "${tag}" to ${email}`,
            CUSTOMER_UPDATE_MUTATION,
            { input: { id: existing.id, tags: finalTags } },
        );
        return { action: "update", existing, finalTags, request };
    }

    const finalTags = [tag];
    const request = client.buildGqlRequest(
        `Shopify customerCreate — new customer ${email} with "${tag}"`,
        CUSTOMER_CREATE_MUTATION,
        {
            input: {
                email,
                firstName: createInput?.firstName ?? "",
                lastName: createInput?.lastName ?? "",
                ...(createInput?.phone ? { phone: createInput.phone } : {}),
                tags: finalTags,
            },
        },
    );
    return { action: "create", existing: null, finalTags, request };
}

/** Send a planned customer-tag mutation and parse create/update userErrors. */
export async function executeCustomerTag(
    client: ShopifyClient,
    plan: CustomerTagPlan,
): Promise<CustomerOpResult> {
    if (plan.action === "noop" || !plan.request) {
        return { ok: true, customer: plan.existing };
    }

    const body = await client.executeRaw(plan.request);
    const topErrors = body.errors?.map((e) => e.message) ?? [];
    if (topErrors.length > 0 && body.data == null) {
        return { ok: false, customer: null, error: topErrors.join(", ") };
    }

    const data = body.data as Partial<CustomerCreateResponse & CustomerUpdateResponse> | undefined;
    const payload = data?.customerCreate ?? data?.customerUpdate;
    if (!payload) {
        return { ok: false, customer: null, error: "Unexpected Shopify response shape" };
    }
    if (payload.userErrors.length > 0) {
        return {
            ok: false,
            customer: null,
            error: payload.userErrors.map((e) => e.message).join(", "),
        };
    }
    return { ok: true, customer: payload.customer };
}
