/**
 * Routable payloads the Slack app sends to the ShopifyRefundHandler Lambda.
 *
 * Cancel-order and create-refund are deliberately SEPARATE actions: the Lambda
 * routes on `action`, and we preview each independently. The Lambda owns the
 * actual Shopify mutation; these payloads carry only what it needs to route and
 * build the call without re-fetching — the order ids and the transactions the
 * eval already pulled.
 *
 * Each builder returns a PreparedRequest so the exact bytes can be previewed
 * (dry-run) and later sent (real run) through the same code path.
 */

import type { PreparedRequest } from "../../shared/http/prepared_request.ts";
import type { RefundTransaction } from "./types.ts";
import { REFUND_PROCESS_URL } from "../../config/refunds.ts";

export type RefundType = "original_method" | "store_credit";

/** Shared identity/audit fields every Lambda action carries. */
export interface OrderActionRef {
    /** Shopify GID — what `orderCancel` / `refundCreate` take. */
    orderId: string;
    /** Display name (e.g. "#1234") — logs, idempotency, human reference. */
    orderNumber: string;
    /** Slack user id of the approver — audit trail. */
    approvedBy: string;
    /** Routes the Lambda to its test path (no live Shopify mutation). */
    isTest: boolean;
}

function lambdaRequest(label: string, body: Record<string, unknown>): PreparedRequest {
    return {
        label,
        method: "POST",
        url: REFUND_PROCESS_URL,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        // Pretty-printed for the dry-run preview; the wire `body` is what's sent.
        displayBody: JSON.stringify(body, null, 2),
    };
}

/** Cancel the order (Shopify `orderCancel`). Kept separate from the refund so
 * cancelling never implicitly refunds — the Lambda sets `refund: false`. */
export function buildCancelOrderRequest(o: OrderActionRef): PreparedRequest {
    return lambdaRequest("Cancel order — ShopifyRefundHandler", {
        action: "cancel_order",
        idempotency_key: `cancel:${o.orderNumber}`,
        order_id: o.orderId,
        order_number: o.orderNumber,
        approved_by: o.approvedBy,
        is_test: o.isTest,
    });
}

/** Create the refund (Shopify `refundCreate` for original payment, or store
 * credit). The Lambda routes on `refund_to` and uses `transactions` to build
 * the refund transactions without re-querying. */
export function buildCreateRefundRequest(
    o: OrderActionRef,
    refund: { refundType: RefundType; amount: number; transactions?: RefundTransaction[] },
): PreparedRequest {
    return lambdaRequest("Create refund — ShopifyRefundHandler", {
        action: "create_refund",
        idempotency_key: `refund:${o.orderNumber}:${refund.refundType}:${refund.amount.toFixed(2)}`,
        order_id: o.orderId,
        order_number: o.orderNumber,
        refund_to: refund.refundType,
        amount: refund.amount,
        // Echoed from the eval (order's payment transactions) so the Lambda
        // builds refundCreate transactions without a re-fetch. Empty until the
        // Lambda populates `transactions` on the evaluation payload.
        transactions: refund.transactions ?? [],
        approved_by: o.approvedBy,
        is_test: o.isTest,
    });
}

/** POST a prepared Lambda request. Returns status + body for failure surfacing. */
export async function executeLambdaRequest(
    req: PreparedRequest,
): Promise<{ ok: boolean; status: number; body: string }> {
    const res = await fetch(req.url, {
        method: req.method,
        headers: req.headers,
        body: req.body,
    });
    return { ok: res.ok, status: res.status, body: await res.text() };
}
