Status: keep
Resource: Order
Path: backend/src/clients/shopify/queries/order_cancel.graphql
Generated: shopify/generated/order_cancel.py

```graphql
mutation OrderCancel(
  $orderId: ID!, $reason: OrderCancelReason!, $restock: Boolean!,
  $notifyCustomer: Boolean, $staffNote: String,
  $refundMethod: OrderCancelRefundMethodInput
) {
  orderCancel(
    orderId: $orderId, reason: $reason, restock: $restock,
    notifyCustomer: $notifyCustomer, staffNote: $staffNote,
    refundMethod: $refundMethod
  ) {
    job { id done }
    orderCancelUserErrors { field message code }
  }
}
```

Note: uses `orderCancelUserErrors` (not `userErrors`). Async — returns a `job`.
