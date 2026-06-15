/**
 * Shopify product operations.
 */

import type { ShopifyClient } from "./client.ts";
import { PRODUCT_BY_HANDLE_QUERY } from "./types/products.ts";
import type { ProductsSearchResponse, ShopifyProduct } from "./types/products.ts";

const log = (fn: string, ...args: unknown[]) => console.log(`[shopify:${fn}]`, ...args);

/**
 * Find a product by its exact handle.
 *
 * Shopify search syntax (https://shopify.dev/docs/api/usage/search-syntax):
 *  - Matching is CASE-INSENSITIVE, so the handle's casing doesn't matter.
 *  - Unquoted values are tokenized into terms with flexible (OR/AND) matching, so a
 *    hyphenated handle like `2026-summer-kickball-sunday-opendiv` would match loosely
 *    on its parts and could return unrelated products.
 *  - Wrapping the value in single quotes forces an exact phrase match.
 * We therefore quote the handle (`handle:'<handle>'`) and additionally require an
 * exact `handle` equality on the result, so the lookup is unambiguous.
 */
export async function findProductByHandle(
    client: ShopifyClient,
    handle: string,
): Promise<ShopifyProduct | null> {
    const { data, errors } = await client.gql<ProductsSearchResponse>(PRODUCT_BY_HANDLE_QUERY, {
        query: `handle:'${handle}'`,
    });

    if (errors.length > 0 || !data) {
        log("findProductByHandle", `${handle} → failed: ${errors.join(", ")}`);
        return null;
    }

    const product = data.products.nodes.find((p) => p.handle === handle) ?? null;
    log("findProductByHandle", `${handle} → ${product ? product.id : "not found"}`);
    return product;
}
