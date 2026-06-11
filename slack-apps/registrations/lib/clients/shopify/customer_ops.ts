/**
 * Shopify customer operations — focused, composable functions.
 */

import type { ShopifyClient } from "./client.ts";
import type {
    CreateCustomerInput,
    CustomerCreateResponse,
    CustomerOpResult,
    CustomerSearchResponse,
    CustomerUpdateResponse,
    ShopifyCustomer,
    UpdateCustomerInput,
} from "./types/customers.ts";

function addTagIfMissing(existingTags: string[], newTag: string): string[] {
    if (existingTags.includes(newTag)) return existingTags;
    return [...existingTags, newTag];
}

const log = (fn: string, ...args: unknown[]) => console.log(`[shopify:${fn}]`, ...args);

const CUSTOMER_FIELDS = `
  id email firstName lastName phone tags note
  state createdAt updatedAt
  lastOrder { id createdAt }
  defaultAddress {
    id address1 address2 city province provinceCode zip phone firstName lastName
  }
`;

export async function findCustomerByEmail(
    client: ShopifyClient,
    email: string,
): Promise<ShopifyCustomer | null> {
    log("findCustomerByEmail", { email });
    const query = `
        query searchCustomer($query: String!) {
            customers(first: 1, query: $query) {
                nodes { ${CUSTOMER_FIELDS} }
            }
        }
    `;
    const { data, errors } = await client.gql<CustomerSearchResponse>(query, {
        query: `email:${email}`,
    });
    if (errors.length > 0 || !data) return null;
    const customer = data.customers.nodes[0] ?? null;
    log("findCustomerByEmail", customer ? `found id=${customer.id}` : "not found");
    return customer;
}

export async function createCustomer(
    client: ShopifyClient,
    input: CreateCustomerInput,
): Promise<CustomerOpResult> {
    log("createCustomer", { email: input.email, tags: input.tags });
    const query = `
        mutation createCustomer($input: CustomerInput!) {
            customerCreate(input: $input) {
                customer { ${CUSTOMER_FIELDS} }
                userErrors { field message }
            }
        }
    `;
    const vars = {
        firstName: input.firstName,
        lastName: input.lastName,
        email: input.email,
        ...(input.phone ? { phone: input.phone } : {}),
        ...(input.note ? { note: input.note } : {}),
        tags: input.tags || [],
    };
    const { data, errors } = await client.gql<CustomerCreateResponse>(query, { input: vars });

    if (errors.length > 0 || !data) return { ok: false, customer: null, error: errors.join(", ") };
    if (data.customerCreate.userErrors.length > 0) {
        return {
            ok: false,
            customer: null,
            error: data.customerCreate.userErrors.map((e) => e.message).join(", "),
        };
    }
    return { ok: true, customer: data.customerCreate.customer };
}

export async function updateCustomer(
    client: ShopifyClient,
    input: UpdateCustomerInput,
): Promise<CustomerOpResult> {
    const query = `
        mutation updateCustomer($input: CustomerInput!) {
            customerUpdate(input: $input) {
                customer { ${CUSTOMER_FIELDS} }
                userErrors { field message }
            }
        }
    `;
    const vars: Record<string, unknown> = { id: input.id };
    if (input.firstName !== undefined) vars.firstName = input.firstName;
    if (input.lastName !== undefined) vars.lastName = input.lastName;
    if (input.email !== undefined) vars.email = input.email;
    if (input.tags) vars.tags = input.tags;
    if (input.phone) vars.phone = input.phone;
    if (input.note !== undefined) vars.note = input.note;

    const { data, errors } = await client.gql<CustomerUpdateResponse>(query, { input: vars });

    if (errors.length > 0 || !data) return { ok: false, customer: null, error: errors.join(", ") };
    if (data.customerUpdate.userErrors.length > 0) {
        return {
            ok: false,
            customer: null,
            error: data.customerUpdate.userErrors.map((e) => e.message).join(", "),
        };
    }
    return { ok: true, customer: data.customerUpdate.customer };
}

export async function addTagToCustomer(
    client: ShopifyClient,
    customerId: string,
    existingTags: string[],
    tag: string,
): Promise<CustomerOpResult> {
    log("addTagToCustomer", { customerId, tag, existingCount: existingTags.length });
    const updatedTags = addTagIfMissing(existingTags, tag);
    if (updatedTags.length === existingTags.length) {
        return { ok: true, customer: null };
    }
    return await updateCustomer(client, { id: customerId, tags: updatedTags });
}

export async function findOrCreateCustomerWithTag(
    client: ShopifyClient,
    email: string,
    tag: string,
    createInput?: Omit<CreateCustomerInput, "email" | "tags">,
): Promise<CustomerOpResult & { created: boolean }> {
    log("findOrCreateCustomerWithTag", { email, tag });
    const existing = await findCustomerByEmail(client, email);
    if (existing) {
        const tagResult = await addTagToCustomer(client, existing.id, existing.tags, tag);
        return { ...tagResult, customer: tagResult.customer ?? existing, created: false };
    }
    const createResult = await createCustomer(client, {
        email,
        firstName: createInput?.firstName ?? "",
        lastName: createInput?.lastName ?? "",
        ...(createInput?.phone ? { phone: createInput.phone } : {}),
        tags: [tag],
    });
    return { ...createResult, created: true };
}
