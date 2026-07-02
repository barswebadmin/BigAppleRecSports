Status: keep (new — added 2026-07-01 for DRY pass)
Path: backend/src/clients/shopify/queries/fragments/files_user_error.graphql
Generated: `FilesUserError` in `generated/fragments.py`

```graphql
fragment FilesUserError on FilesUserError {
  field
  message
  code
}
```

Composes: nothing (leaf).

Used by: `FileCreate`, `FileUpdate`, `FileDelete`.

Schema note: separate from `UserError` because Files mutations return their own `[FilesUserError!]!` type — includes the extra `code: FilesErrorCode` field that the generic `UserError` lacks.
