Status: keep (regenerated)
Path: backend/src/clients/shopify/generated/enums.py

Codegen'd `str, Enum` classes:

- Locale/money: `CountryCode`, `CurrencyCode`, `WeightUnit`, `TaxExemption`, `UnitPriceMeasurementMeasuredUnit`
- Customer state: `CustomerState`, `CustomerEmailMarketingState`, `CustomerSmsMarketingState`, `CustomerMarketingOptInLevel`
- Order: `OrderCancelReason`, `OrderCancelUserErrorCode`, `OrderTransactionKind`, `OrderTransactionStatus`, `OrderAdjustmentInputDiscrepancyReason`
- Product: `ProductStatus`, `ProductVariantInventoryPolicy`, `ProductVariantsBulkUpdateUserErrorCode`
- Refund: `RefundDutyRefundType`, `RefundLineItemRestockType`

These supersede the hand-written enums in `models/gql_models.py`
(`OrderCancelReason`, `OrderStatus`, `ProductStatus`, `RefundType`,
`DiscountType`) — the codegen names should win at call sites.
