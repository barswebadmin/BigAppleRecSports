import { DefineType, Schema } from "deno-slack-sdk/mod.ts";

export const RefundRequestType = DefineType({
    title: "Refund Request",
    description: "Refund request details",
    name: "refund_request",
    type: Schema.types.object,
    properties: {
        created_at: { type: Schema.types.string },
        order_number: { type: Schema.types.string },
        first_name: { type: Schema.types.string },
        last_name: { type: Schema.types.string },
        email_address: { type: Schema.types.string },
        refund_type: { type: Schema.types.string },
        notes: { type: Schema.types.string },
    },
    required: [
        "created_at",
        "order_number",
        "first_name",
        "last_name",
        "email_address",
        "refund_type",
    ],
});
