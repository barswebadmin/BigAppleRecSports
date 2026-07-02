Status: superseded (2026-07-01) — new op `InventoryAdjustQuantities` at `backend/src/clients/shopify/queries/inventory_adjust_quantities.graphql`; tracker at `structure/mutations/new/InventoryAdjustQuantities.md`
Resource: Variant / Inventory
Path: backend/lib/clients/shopify_client_old/queries/variants.py → `AdjustInventory`
Replacement: **`InventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!)`**. Legacy helper hardcoded `reason: "correction"` and `name: "available"` — that shape logic moves to the call site as a builder.

```graphql
mutation adjustInventory($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup {
      reason
      changes { name delta quantityAfterChange }
    }
    userErrors { field message }
  }
}
```

Input shape hard-codes `reason: "correction"`, `name: "available"` — the
existing helper builds the input dict, which is fine to keep at the call site
or wrap in a small helper.
