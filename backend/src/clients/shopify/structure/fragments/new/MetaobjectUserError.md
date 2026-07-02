Status: keep (new — added 2026-07-01)
Path: backend/src/clients/shopify/queries/fragments/metaobject_user_error.graphql
Generated: `MetaobjectUserError` in `generated/fragments.py`

```graphql
fragment MetaobjectUserError on MetaobjectUserError {
  field
  message
  code
  elementIndex
  elementKey
}
```

Composes: nothing (leaf).

Used by: `MetaobjectDefinitionCreate`, `MetaobjectCreate`.

Schema note: `MetaobjectUserError` has richer fields than generic `UserError` — includes `code: MetaobjectUserErrorCode`, `elementIndex: Int` (array position of the failing element), `elementKey: String` (object key). All four fields useful for the population scripts that deal with batch metaobject creation.
