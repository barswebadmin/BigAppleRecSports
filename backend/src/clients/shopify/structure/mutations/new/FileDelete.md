Status: keep (new — added 2026-07-01)
Resource: Media / File
Path: backend/src/clients/shopify/queries/file_delete.graphql
Generated: backend/src/clients/shopify/generated/file_delete.py (regenerate on next `just codegen-shopify`)

```graphql
mutation FileDelete($fileIds: [ID!]!) {
  fileDelete(fileIds: $fileIds) {
    deletedFileIds
    userErrors { field message code }
  }
}
```

Permanently removes files from the Files library.

**Per Shopify's schema docstring**: "When you delete files that are referenced by products, the mutation automatically removes those references and reorders any remaining media to maintain proper positioning." So `FileDelete` = full nuke; `FileUpdate(referencesToRemove:)` = per-product detach with the file surviving. Pick the right one for the semantic.

Warning from the schema: "File deletion is permanent and can't be undone. When you delete a file that's being used in your store, it will immediately stop appearing wherever it was displayed."

No legacy equivalent — the old client only had `DeleteProductMedia` (detach, uses deprecated `productDeleteMedia`). This is a new capability.

BARS use: probably rare — cleanup of abandoned uploads, retired branding. Not part of any operational flow yet.
