/**
 * Prepared requests for refund approval: either the legacy ShopifyRefundHandler
 * Lambda (`REFUND_PROCESS_URL`) or the BARS FastAPI backend when
 * `BARS_API_URL` is set.
 */

import type { PreparedRequest } from "../../shared/http/prepared_request.ts";
import type { OrderActionRef, RefundTransaction, RefundType } from "./types.ts";
import { barsApiBaseUrl, REFUND_PROCESS_URL } from "../../config/store.ts";

/** True when approval actions should hit the BARS API (`/refunds/create`, `DELETE /orders/...`). */
export function barsApiConfigured(): boolean {
    return Boolean(barsApiBaseUrl());
}

function buildPost(label: string, url: string, body: Record<string, unknown>): PreparedRequest {
    const serialized = JSON.stringify(body);
    return {
        label,
        method: "POST",
        url,
        headers: { "Content-Type": "application/json" },
        body: serialized,
        displayBody: JSON.stringify(body, null, 2),
    };
}

/** Cancel the order (Shopify `orderCancel`). Kept separate from the refund so
 *  cancelling never implicitly refunds — the Lambda sets `refund: false`. */
export function buildCancelOrderRequest(o: OrderActionRef): PreparedRequest {
    return buildPost("Cancel order — ShopifyRefundHandler", REFUND_PROCESS_URL, {
        action: "cancel_order",
        idempotency_key: `cancel:${o.orderNumber}`,
        order_id: o.orderId,
        order_number: o.orderNumber,
        approved_by: o.approvedBy,
        is_test: o.isTest,
    });
}

/** Create the refund (Shopify `refundCreate` for original payment, or store
 *  credit). The Lambda routes on `refund_to` and uses `transactions` to build
 *  the refund transactions without re-querying. */
export function buildCreateRefundRequest(
    o: OrderActionRef,
    refund: { refundType: RefundType; amount: number; transactions?: RefundTransaction[] },
): PreparedRequest {
    return buildPost("Create refund — ShopifyRefundHandler", REFUND_PROCESS_URL, {
        action: "create_refund",
        idempotency_key: `refund:${o.orderNumber}:${refund.refundType}:${refund.amount.toFixed(2)}`,
        order_id: o.orderId,
        order_number: o.orderNumber,
        refund_to: refund.refundType,
        amount: refund.amount,
        transactions: refund.transactions ?? [],
        approved_by: o.approvedBy,
        is_test: o.isTest,
    });
}

/** `POST /refunds/create` — optional cancel + refund in one request. */
export function buildBackendRefundCreateRequest(
    o: OrderActionRef,
    args: {
        cancelOrder: boolean;
        refundType: RefundType;
        amount: number;
        transactions?: RefundTransaction[];
        currency?: string | null;
        notify?: boolean;
    },
): PreparedRequest {
    const base = barsApiBaseUrl();
    if (!base) {
        throw new Error("BARS_API_URL is not set");
    }
    const idempotencyKey = `refund:${o.orderNumber}:${args.refundType}:${args.amount.toFixed(2)}`;
    return buildPost("Refund / cancel — BARS backend", `${base}/refunds/create`, {
        cancelOrder: args.cancelOrder,
        orderId: o.orderId,
        orderNumber: o.orderNumber,
        refundTo: args.refundType,
        amount: args.amount,
        transactions: args.transactions ?? [],
        approvedBy: o.approvedBy,
        isTest: o.isTest,
        currency: args.currency ?? undefined,
        notify: args.notify ?? false,
        idempotencyKey,
    });
}

/** `DELETE /orders/{orderId}` — cancel only (no refund). */
export function buildBackendOrderCancelRequest(o: OrderActionRef): PreparedRequest {
    const base = barsApiBaseUrl();
    if (!base) {
        throw new Error("BARS_API_URL is not set");
    }
    const url = `${base}/orders/${encodeURIComponent(o.orderId)}`;
    const body = {
        reason: "CUSTOMER",
        restock: false,
        notify_customer: false,
        staff_note: `Slack-approved cancel (by ${o.approvedBy})`,
    };
    const serialized = JSON.stringify(body);
    return {
        label: "Cancel order — BARS backend",
        method: "DELETE",
        url,
        headers: { "Content-Type": "application/json" },
        body: serialized,
        displayBody: JSON.stringify(body, null, 2),
    };
}

/** POST a prepared action request. Returns status + body for failure surfacing. */
export async function executeActionRequest(
    req: PreparedRequest,
): Promise<{ ok: boolean; status: number; body: string }> {
    const res = await fetch(req.url, {
        method: req.method,
        headers: req.headers,
        body: req.body,
    });
    return { ok: res.ok, status: res.status, body: await res.text() };
}
