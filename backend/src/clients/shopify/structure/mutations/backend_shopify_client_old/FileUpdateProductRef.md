Status: superseded (2026-07-01) — new op `FileUpdate` at `backend/src/clients/shopify/queries/file_update.graphql`; tracker at `structure/mutations/new/FileUpdate.md`
Resource: Media / File
Path: backend/lib/clients/shopify_client_old/queries/media.py → `FileUpdateProductRef`
Replacement: **`FileUpdate($files: [FileUpdateInput!]!)`** — same underlying `fileUpdate` mutation, richer selection. Callers pass `[{id: fileGid, referencesToAdd: [productGid]}]` to attach or `[{id: fileGid, referencesToRemove: [productGid]}]` to detach.

```graphql
mutation fileUpdateProductRef($files: [FileUpdateInput!]!) {
  fileUpdate(files: $files) {
    files { id }
    userErrors { field message }
  }
}
```

Semantic: associate or dissociate a Content > Files library file with a product
(via `referencesToAdd` / `referencesToRemove`). The attach/detach branching
lives in the helper, not the GQL — belongs at the call site or in a tiny
wrapper.
