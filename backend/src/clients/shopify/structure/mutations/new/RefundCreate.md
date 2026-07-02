Status: keep
Resource: Refund
Path: backend/src/clients/shopify/queries/refund_create.graphql
Generated: shopify/generated/refund_create.py

```graphql
mutation RefundCreate($input: RefundInput!, $idempotencyKey: String!) {
  refundCreate(input: $input) @idempotent(key: $idempotencyKey) {
    refund {
      id note createdAt
      totalRefundedSet { presentmentMoney { amount currencyCode } }
      order { id name }
    }
    userErrors { field message }
  }
}
```

Uses the `@idempotent(key:)` directive. Note: `presentmentMoney` here vs
`shopMoney` in the `Order` fragment — deliberate; refund flow needs the
customer-facing currency.
