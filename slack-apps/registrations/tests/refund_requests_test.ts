import { assertEquals } from "@std/assert";
import {
    buildCancelOrderRequest,
    buildCreateRefundRequest,
    type OrderActionRef,
} from "../lib/refunds/lambda_requests.ts";
import type { RefundTransaction } from "../types/evaluation_payload.ts";

const orderRef: OrderActionRef = {
    orderId: "gid://shopify/Order/456",
    orderNumber: "#1001",
    approvedBy: "U_APPROVER",
    isTest: true,
};

const transactions: RefundTransaction[] = [{
    id: "gid://shopify/OrderTransaction/1",
    kind: "SALE",
    status: "SUCCESS",
    gateway: "shopify_payments",
    parent_id: null,
}];

Deno.test("buildCancelOrderRequest produces expected Lambda body", () => {
    const req = buildCancelOrderRequest(orderRef);
    assertEquals(JSON.parse(req.body!), {
        action: "cancel_order",
        idempotency_key: "cancel:#1001",
        order_id: "gid://shopify/Order/456",
        order_number: "#1001",
        approved_by: "U_APPROVER",
        is_test: true,
    });
});

Deno.test("buildCreateRefundRequest produces expected Lambda body", () => {
    const req = buildCreateRefundRequest(orderRef, {
        refundType: "refund_to_original",
        amount: 67.5,
        transactions,
    });
    assertEquals(JSON.parse(req.body!), {
        action: "create_refund",
        idempotency_key: "refund:#1001:refund_to_original:67.50",
        order_id: "gid://shopify/Order/456",
        order_number: "#1001",
        refund_type: "refund_to_original",
        amount: 67.5,
        transactions,
        approved_by: "U_APPROVER",
        is_test: true,
    });
});

Deno.test("buildCreateRefundRequest defaults transactions to empty array", () => {
    const req = buildCreateRefundRequest(orderRef, {
        refundType: "store_credit",
        amount: 50,
    });
    const body = JSON.parse(req.body!);
    assertEquals(body.transactions, []);
    assertEquals(body.idempotency_key, "refund:#1001:store_credit:50.00");
});
