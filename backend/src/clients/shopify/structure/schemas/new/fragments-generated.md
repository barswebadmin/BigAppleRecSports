Status: keep (regenerated)
Path: backend/src/clients/shopify/generated/fragments.py

Ariadne-codegen output for the two source fragments.

Customer surface:
- `Customer`
- `CustomerDefaultEmailAddress`
- `CustomerDefaultPhoneNumber`
- `OrderCustomer(Customer)` — reused inside the Order fragment via subclass

Order surface:
- `Order`
- Money bags: `OrderTotalPriceSet[+ShopMoney]`, `OrderTotalDiscountsSet[+ShopMoney]`, `OrderTotalRefundedSet[+ShopMoney]`
- Line items: `OrderLineItems`, `OrderLineItemsNodes`, `OrderLineItemsNodesCustomAttributes`, `OrderLineItemsNodesVariant`, `OrderLineItemsNodesProduct`
- Transactions: `OrderTransactions`, `OrderTransactionsParentTransaction`
- Refunds: `OrderRefunds`, `OrderRefundsTotalRefundedSet[+ShopMoney]`, `OrderRefundsTransactions`, `OrderRefundsTransactionsNodes`, `OrderRefundsTransactionsNodesAmountSet[+ShopMoney]`

Every field access surfaces as an attribute on a typed pydantic model — no
`payload["camelCaseKey"]` at call sites.
