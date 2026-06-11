/**
 * Export Shopify Orders for a Product → CSV.
 *
 * Mirrors scripts/shopify/export_product_orders.py.
 *
 * Usage (as a CLI):
 *     deno run --allow-net --allow-env --allow-read --allow-write \
 *         lib/exports/export_product_orders.ts <PRODUCT_ID_OR_URL>
 *
 * Output:
 *     ~/Documents/shopify_orders_for_<product_id>.csv
 *
 * Required env (loaded from process env; use `dotenv` or `--env-file`):
 *     SHOPIFY__URL__API_GRAPH_QL
 *     SHOPIFY__TOKEN__ADMIN
 */

import { stringify } from "@std/csv";
import { createShopifyClient, ShopifyClient } from "../clients/shopify/client.ts";

export const ORDERS_QUERY = `
query getOrdersByProduct($query: String!, $first: Int!, $after: String) {
  orders(first: $first, after: $after, query: $query) {
    nodes {
      id
      name
      createdAt
      cancelledAt
      totalPriceSet { shopMoney { amount currencyCode } }
      customer { id email firstName lastName tags }
      customAttributes { key value }
      lineItems(first: 250) {
        nodes {
          id
          title
          quantity
          customAttributes { key value }
          variant { id title }
          product { id }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
`;

type Primitive = string | number | boolean | null;
type JsonValue = Primitive | JsonValue[] | { [key: string]: JsonValue };
type JsonObject = { [key: string]: JsonValue };

interface OrdersPage {
    orders: {
        nodes: JsonObject[];
        pageInfo: { hasNextPage: boolean; endCursor: string | null };
    };
}

export async function fetchOrdersPage(
    client: ShopifyClient,
    productId: string,
    cursor: string | null,
): Promise<{ orders: JsonObject[]; nextCursor: string | null }> {
    const variables: Record<string, unknown> = {
        query: `product_id:${productId}`,
        first: 100,
    };
    if (cursor) variables.after = cursor;

    const result = await client.gqlClassified<OrdersPage>(
        ORDERS_QUERY,
        variables,
    );

    if (result.kind !== "OK" && result.kind !== "NO_CONTENT") {
        throw new Error(`Shopify ${result.kind}: ${result.errors.join("; ")}`);
    }

    const ordersData = result.data?.orders;
    const orders = ordersData?.nodes ?? [];
    const pageInfo = ordersData?.pageInfo ??
        { hasNextPage: false, endCursor: null };
    const nextCursor = pageInfo.hasNextPage ? pageInfo.endCursor : null;

    return { orders, nextCursor };
}

export async function fetchAllOrders(
    client: ShopifyClient,
    productId: string,
): Promise<JsonObject[]> {
    const all: JsonObject[] = [];
    let cursor: string | null = null;
    let pageNum = 1;

    while (true) {
        const { orders, nextCursor } = await fetchOrdersPage(
            client,
            productId,
            cursor,
        );
        all.push(...orders);
        console.error(
            `  Page ${pageNum}: ${orders.length} orders (total: ${all.length})`,
        );
        if (!nextCursor) break;
        cursor = nextCursor;
        pageNum++;
    }

    return all;
}

export function flattenObject(
    obj: JsonValue,
    prefix = "",
): Record<string, string | number | boolean> {
    const out: Record<string, string | number | boolean> = {};

    const flatten = (value: JsonValue, currentPrefix: string): void => {
        if (value === null || value === undefined) {
            out[currentPrefix] = "";
            return;
        }
        if (Array.isArray(value)) {
            value.forEach((item, i) => {
                const key = `${currentPrefix}[${i}]`;
                if (item !== null && typeof item === "object") {
                    flatten(item, key);
                } else {
                    out[key] = item === null ? "" : item;
                }
            });
            return;
        }
        if (typeof value === "object") {
            for (const [k, v] of Object.entries(value)) {
                const key = currentPrefix ? `${currentPrefix}.${k}` : k;
                if (v !== null && typeof v === "object") {
                    flatten(v, key);
                } else {
                    out[key] = v === null ? "" : v;
                }
            }
            return;
        }
        out[currentPrefix] = value;
    };

    flatten(obj, prefix);
    return out;
}

type Row = Record<string, string | number | boolean>;

export function extractOrderRow(order: JsonObject): Row {
    const row: Row = {};
    const lineItemsContainer = order.lineItems as
        | { nodes?: JsonObject[] }
        | undefined;
    const lineItems = lineItemsContainer?.nodes ?? [];

    for (const [key, value] of Object.entries(order)) {
        if (key === "lineItems") continue;

        if (key === "customAttributes") {
            const attrs = (value ?? []) as { key?: string; value?: string }[];
            for (const attr of attrs) {
                if (attr.key) {
                    row[`customAttributes.${attr.key}`] = attr.value ?? "";
                }
            }
            continue;
        }

        if (value !== null && typeof value === "object") {
            const flat = flattenObject(value, key);
            for (const [fk, fv] of Object.entries(flat)) row[fk] = fv;
        } else {
            row[key] = value === null ? "" : value;
        }
    }

    if (lineItems.length > 0) {
        const first = lineItems[0];
        for (const [key, value] of Object.entries(first)) {
            if (key === "customAttributes") continue;
            const col = `lineItems.${key}`;
            if (value !== null && typeof value === "object") {
                const flat = flattenObject(value, col);
                for (const [fk, fv] of Object.entries(flat)) row[fk] = fv;
            } else {
                row[col] = value === null ? "" : value;
            }
        }
    }

    for (const item of lineItems) {
        const attrs = (item.customAttributes ?? []) as {
            key?: string;
            value?: string;
        }[];
        for (const attr of attrs) {
            if (attr.key) {
                const col = `lineItems.customAttributes.${attr.key}`;
                if (!(col in row)) row[col] = attr.value ?? "";
            }
        }
    }

    return row;
}

export function buildCsv(orders: JsonObject[]): string {
    const rows = orders.map(extractOrderRow);
    const allColumns = new Set<string>();
    for (const row of rows) {
        for (const col of Object.keys(row)) allColumns.add(col);
    }

    const isCustomAttr = (c: string) =>
        c.startsWith("customAttributes.") ||
        c.startsWith("lineItems.customAttributes.");
    const customCols = [...allColumns].filter(isCustomAttr).sort();
    const otherCols = [...allColumns].filter((c) => !isCustomAttr(c)).sort();
    const columns = [...otherCols, ...customCols];

    const data = rows.map((row) => Object.fromEntries(columns.map((c) => [c, row[c] ?? ""])));

    return stringify(data, { columns, headers: true });
}

export function extractProductId(input: string): string {
    const trimmed = input.trim();
    if (trimmed.includes("/")) {
        const parts = trimmed.replace(/\/$/, "").split("/");
        return parts[parts.length - 1];
    }
    return trimmed;
}

export async function exportOrdersForProduct(
    client: ShopifyClient,
    productId: string,
    outputPath: string,
): Promise<{ count: number; outputPath: string }> {
    const orders = await fetchAllOrders(client, productId);
    if (orders.length === 0) return { count: 0, outputPath };
    const csv = buildCsv(orders);
    await Deno.writeTextFile(outputPath, csv);
    return { count: orders.length, outputPath };
}

async function main(): Promise<void> {
    const arg = Deno.args[0];
    if (!arg) {
        console.error("Usage: export_product_orders.ts <PRODUCT_ID_OR_URL>");
        Deno.exit(1);
    }
    const productId = extractProductId(arg);

    const env = Deno.env.toObject();
    const client = createShopifyClient(env);

    console.error(`🔍 Fetching orders for product ${productId}...`);
    const orders = await fetchAllOrders(client, productId);

    if (orders.length === 0) {
        console.error(`⚠️ No orders found for product ${productId}`);
        Deno.exit(0);
    }

    console.error(`✅ Found ${orders.length} total orders`);

    const home = env.HOME ?? env.USERPROFILE ?? "";
    if (!home) throw new Error("Unable to resolve home directory");
    const outputDir = `${home}/Documents`;
    await Deno.mkdir(outputDir, { recursive: true });
    const outputPath = `${outputDir}/shopify_orders_for_${productId}.csv`;

    const csv = buildCsv(orders);
    await Deno.writeTextFile(outputPath, csv);

    console.log(`📄 Exported to: ${outputPath}`);
}

if (import.meta.main) {
    await main();
}
