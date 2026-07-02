Status: keep (new — added 2026-07-01 for DRY pass)
Path: backend/src/clients/shopify/queries/fragments/user_error.graphql
Generated: `UserError` in `generated/fragments.py`

```graphql
fragment UserError on UserError {
  field
  message
}
```

Composes: nothing (leaf).

Used by: `CustomerUpdate`, `ProductUpdate`, `RefundCreate`, `TagsUpdate` (×2 — `added.userErrors` + `removed.userErrors`).

Schema note: `UserError` is a **concrete type** (not an interface) in the Shopify schema — it `implements DisplayableError` but the payloads that return `[UserError!]!` (CustomerUpdate, ProductUpdate, RefundCreate, TagsAdd, TagsRemove) all use this concrete type. Other mutations use their own specific error types (`FilesUserError`, `OrderCancelUserError`, `ProductVariantsBulkUpdateUserError`) — those have their own fragments (or no fragment if used only once).
