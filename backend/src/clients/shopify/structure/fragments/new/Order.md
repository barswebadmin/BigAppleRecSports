Status: keep — refactored 2026-07-01 for DRY (spreads `Customer`, `MoneyBag`, `Refund`)
Path: backend/src/clients/shopify/queries/fragments/order.graphql
Generated model: `Order` (+ many nested subclasses) in `generated/fragments.py`

# Order fragment

Composes:
- `Customer` — via `customer { ...Customer }` → codegen surfaces `OrderCustomer(Customer)` subclass.
- `MoneyBag` — via `totalPriceSet { ...MoneyBag }`, `totalDiscountsSet { ...MoneyBag }`, `totalRefundedSet { ...MoneyBag }`.
- `Refund` — via `refunds { ...Refund }` (each refund gets the full `Refund` fragment which itself uses `MoneyBag`).

Selection set (grouped):
- Scalars: `id`, `name`, `email`, `phone`, `createdAt`, `updatedAt`, `cancelledAt`, `cancelReason`, `note`, `tags`
- Money (3× `MoneyBag`): `totalPriceSet`, `totalDiscountsSet`, `totalRefundedSet`
- `lineItems(first: 250)`: `id`, `title`, `customAttributes{key,value}`, `variant{id,title}`, `product{id,title}` (still inline — no `LineItem` fragment yet; add when a second consumer arises)
- `transactions`: `id`, `kind`, `status`, `gateway`, `parentTransaction{id}` (inline; only used inside Order today)
- `customer { ...Customer }`
- `refunds { ...Refund }`

Composed into: `OrdersGet`, `GetOrder`.

Deferred fragment candidates (add if a second consumer appears): `LineItem`, `OrderTransactionBrief`.
