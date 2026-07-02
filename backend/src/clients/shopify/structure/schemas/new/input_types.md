Status: keep (regenerated)
Path: backend/src/clients/shopify/generated/input_types.py

Codegen'd `BaseModel` inputs referenced by the current op set:

Customer:
- `CustomerInput` — used by `CustomerUpdate`
- `CustomerEmailMarketingConsentInput`
- `CustomerSmsMarketingConsentInput`

Order:
- `OrderCancelRefundMethodInput` (+ `OrderCancelStoreCreditRefundInput`)
- `OrderTransactionInput`

Product:
- `ProductUpdateInput` — used by `ProductUpdate`

Variant / Inventory:
- `ProductVariantsBulkInput` — used by `ProductVariantsBulkUpdate`
- `InventoryAdjustmentInput`, `InventoryItemInput`, `InventoryItemMeasurementInput`, `InventoryLevelInput`

Refund:
- `RefundInput` — used by `RefundCreate`
- `RefundLineItemInput`, `RefundDutyInput`, `RefundMethodInput`, `StoreCreditRefundInput`, `ShippingRefundInput`

Shared / miscellaneous:
- `MetafieldInput` (used when we fold in the metafield-link case of `productUpdate`)
- `MoneyInput`, `WeightInput`, `SEOInput`, `UnitPriceMeasurementInput`, `VariantOptionValueInput`, `CountryHarmonizedSystemCodeInput`

Filtered by `shopify/schema_filter_config.json` — extending the op set may
require widening that filter and regenerating.
