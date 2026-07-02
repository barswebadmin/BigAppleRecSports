Status: keep (new — added 2026-07-01)
Resource: Variant / Inventory
Path: backend/src/clients/shopify/queries/inventory_adjust_quantities.graphql
Generated: backend/src/clients/shopify/generated/inventory_adjust_quantities.py

```graphql
mutation InventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    inventoryAdjustmentGroup {
      id
      reason
      changes {
        name delta quantityAfterChange
        item { id sku }
      }
    }
    userErrors { field message code }
  }
}
```

Fragments used: none — `InventoryAdjustQuantitiesUserError` is only used by this one op, so no fragment gain (kept inline: `field message code`).

Supersedes legacy `AdjustInventory` (from `queries/variants.py`). Legacy helper hardcoded `reason: "correction"` and `name: "available"` when building the input dict — that shape logic moves to the call site (a small builder that produces `InventoryAdjustQuantitiesInput`).

BARS use: workhorse for every registration state change — phase transitions (move slots between variants), refund returns, admin corrections. Retired `MoveInventoryLambda`'s core capability.

Callers to migrate later: legacy import path `from lib.clients.shopify_client_old.queries.variants import AdjustInventory`.
