/**
 * Shopify product operations.
 */

import type { ShopifyClient } from "./client.ts";
import { PRODUCT_BY_ID_QUERY } from "./types/products.ts";
import type { ProductByIdResponse } from "./types/products.ts";

const log = (fn: string, ...args: unknown[]) => console.log(`[shopify:${fn}]`, ...args);

export async function getProductHandle(
    client: ShopifyClient,
    productId: number,
): Promise<string | null> {
    const gid = `gid://shopify/Product/${productId}`;
    log("getProductHandle", { gid });

    const { data, errors } = await client.gql<ProductByIdResponse>(PRODUCT_BY_ID_QUERY, {
        id: gid,
    });

    if (errors.length > 0 || !data?.product) {
        log("getProductHandle", `failed: ${errors.join(", ")}`);
        return null;
    }

    log("getProductHandle", `handle: ${data.product.handle}`);
    return data.product.handle;
}
