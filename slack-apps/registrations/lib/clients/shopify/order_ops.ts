/**
 * Shopify order operations — query by name, typed responses.
 */

import type { ShopifyClient } from "./client.ts";
import type { OrderQueryResult, ShopifyOrder } from "./types/orders.ts";
import { normalizeShopifyOrderNumber, ORDER_BY_NAME_QUERY } from "./types/orders.ts";

const log = (fn: string, ...args: unknown[]) => console.log(`[shopify:${fn}]`, ...args);

export async function findOrderByName(
    client: ShopifyClient,
    orderNumber: string,
): Promise<OrderQueryResult> {
    const name = normalizeShopifyOrderNumber(orderNumber);
    log("findOrderByName", { name });

    const { data, errors } = await client.gql<{
        orders: { edges: { node: ShopifyOrder }[] };
    }>(ORDER_BY_NAME_QUERY, { query: `name:${name}` });

    if (errors.length > 0 || !data) {
        return { ok: false, order: null, error: errors.join(", ") };
    }

    const order = data.orders.edges[0]?.node ?? null;
    log("findOrderByName", order ? `found ${order.name}` : "not found");
    return { ok: true, order };
}

import type { ShopifyCustomAttribute } from "./types/orders.ts";

export function getCustomAttribute(
    attrs: ShopifyCustomAttribute[],
    key: string,
): string | undefined {
    const lower = key.toLowerCase();
    return attrs.find((a) => a.key.toLowerCase() === lower)?.value;
}
