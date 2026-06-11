export { LineItemType, RefundType };

import { DefineType, Schema } from "deno-slack-sdk/mod.ts";

export interface ShopifyMoney {
    amount: string;
}

export interface ShopifyRefundLineItem {
    quantity: number;
    priceSet: { shopMoney: ShopifyMoney };
    lineItem: { title: string };
}

export interface ShopifyTransaction {
    id: string;
    status: string;
    kind: string;
    gateway: string;
    amountSet: { shopMoney: ShopifyMoney };
    createdAt: string;
}

export interface ShopifyRefund {
    id: string;
    createdAt: string;
    note: string | null;
    refundLineItems: {
        nodes: ShopifyRefundLineItem[];
    };
    transactions: {
        nodes: ShopifyTransaction[];
    };
}

export interface ShopifyCustomAttribute {
    key: string;
    value: string;
}

import type { ShopifyProduct } from "./products.ts";

export interface ShopifyLineItem {
    title: string;
    quantity: number;
    customAttributes: ShopifyCustomAttribute[];
    product: ShopifyProduct | null;
}

export interface ShopifyOrder {
    id: string;
    name: string;
    createdAt: string;
    cancelledAt: string | null;
    totalPriceSet: { shopMoney: ShopifyMoney };
    customer: {
        id: string;
        firstName: string | null;
        lastName: string | null;
        email: string | null;
    } | null;
    lineItems: {
        edges: { node: ShopifyLineItem }[];
    };
    refunds: ShopifyRefund[];
}

export interface OrderQueryResult {
    ok: boolean;
    order: ShopifyOrder | null;
    error?: string;
}

export const ORDER_FIELDS = `
    id
    name
    createdAt
    cancelledAt
    totalPriceSet { shopMoney { amount } }
    customer {
        id firstName lastName email
    }
    lineItems(first: 3) {
        edges {
            node {
                title
                quantity
                customAttributes { key value }
                product {
                    id
                    handle
                    tags
                    variants(first: 4) { nodes { id title } }
                }
            }
        }
    }
    refunds {
        id
        createdAt
        note
        transactions(first: 5) {
            nodes {
                id status kind gateway createdAt
                amountSet { shopMoney { amount } }
            }
        }
        refundLineItems(first: 3) {
            nodes {
                quantity
                priceSet { shopMoney { amount } }
                lineItem { title }
            }
        }
    }
`;

export const ORDER_BY_NAME_QUERY = `
    query getOrderByName($query: String!) {
        orders(first: 1, query: $query) {
            edges { node { ${ORDER_FIELDS} } }
        }
    }
`;

const LineItemType = DefineType({
    title: "Shopify Line Item",
    name: "shopify_line_item",
    type: Schema.types.object,
    properties: {
        title: { type: Schema.types.string },
        quantity: { type: Schema.types.number },
        unit_price: { type: Schema.types.string },
    },
    required: ["title", "quantity", "unit_price"],
});

const RefundType = DefineType({
    title: "Shopify Refund",
    name: "shopify_refund",
    type: Schema.types.object,
    properties: {
        id: { type: Schema.types.string },
        created_at: { type: Schema.types.string },
        amount: { type: Schema.types.string },
    },
    required: ["id", "created_at", "amount"],
});

export const ShopifyOrderType = DefineType({
    title: "Shopify Order",
    description: "Flattened Shopify order for workflow step passing",
    name: "shopify_order",
    type: Schema.types.object,
    properties: {
        id: { type: Schema.types.string },
        name: { type: Schema.types.string },
        created_at: { type: Schema.types.string },
        email: { type: Schema.types.string },
        total_price: { type: Schema.types.string },
        subtotal_price: { type: Schema.types.string },
        current_subtotal_price: { type: Schema.types.string },
        customer_id: { type: Schema.types.string },
        customer_first_name: { type: Schema.types.string },
        customer_last_name: { type: Schema.types.string },
        customer_email: { type: Schema.types.string },
        line_items: { type: Schema.types.array, items: { type: LineItemType } },
        refunds: { type: Schema.types.array, items: { type: RefundType } },
        refund_count: { type: Schema.types.number },
        total_refunded: { type: Schema.types.string },
    },
    required: ["id", "name", "created_at", "total_price"],
});

export function normalizeShopifyOrderNumber(orderNumber: string): string {
    const trimmed = orderNumber.trim();
    return trimmed.startsWith("#") ? trimmed : `#${trimmed}`;
}
