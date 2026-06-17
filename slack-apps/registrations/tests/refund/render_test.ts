import { assertEquals } from "@std/assert";
import { REFUND_TEST_CHANNEL } from "../../config/refunds.ts";
import { runPostRefundEvaluation } from "../../functions/post_refund_evaluation.ts";
import { buildRefundEvalBlocks } from "../../domain/refund/eval_blocks.ts";
import type { RefundEvaluationPayload } from "../../domain/refund/types.ts";
import { createMockSlackClient } from "../harness.ts";

const samplePayload: RefundEvaluationPayload = {
    is_test: true,
    email: "jane@example.com",
    first_name: "Jane",
    last_name: "Doe",
    refund_to: "original_method",
    sport: "kickball",
    season: "summer",
    day: "sunday",
    division: "open",
    product_id: "gid://shopify/Product/123",
    product_title: "Summer Kickball Sunday",
    order_number: "#1001",
    order_id: "gid://shopify/Order/456",
    order_found: true,
    order_total: 75,
    total_refunded: 0,
    refundable_balance: 75,
    is_cancelled: false,
    validation_passed: true,
    warnings: [],
    season_start_date: "2026-06-01",
    season_week_resolved: "week_1",
    estimated_refund_to_original: {
        success: true,
        amount: 67.5,
        percentage: 90,
        penalty: null,
        timing: "before_season",
        has_processing_fee: false,
        no_payment: false,
        message: null,
    },
    estimated_store_credit: {
        success: true,
        amount: 75,
        percentage: 100,
        penalty: null,
        timing: "before_season",
        has_processing_fee: false,
        no_payment: false,
        message: null,
    },
    transactions: [{
        id: "gid://shopify/OrderTransaction/1",
        kind: "SALE",
        status: "SUCCESS",
        gateway: "shopify_payments",
        parent_id: null,
    }],
    currency_code: "USD",
};

Deno.test("post_refund_evaluation routes is_test to REFUND_TEST_CHANNEL with correct blocks", async () => {
    const { client, calls } = createMockSlackClient();

    const result = await runPostRefundEvaluation(
        { evaluation_json: JSON.stringify(samplePayload) },
        client,
    );

    assertEquals(result, { completed: false });
    assertEquals(calls.length, 1);
    assertEquals(calls[0].method, "chat.postMessage");

    const args = calls[0].args as { channel: string; blocks: unknown };
    assertEquals(args.channel, REFUND_TEST_CHANNEL);
    assertEquals(args.blocks, buildRefundEvalBlocks(samplePayload));
});
