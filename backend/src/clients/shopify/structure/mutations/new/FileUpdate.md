Status: keep (new — added 2026-07-01)
Resource: Media / File
Path: backend/src/clients/shopify/queries/file_update.graphql
Generated: backend/src/clients/shopify/generated/file_update.py (regenerate on next `just codegen-shopify`)

```graphql
mutation FileUpdate($files: [FileUpdateInput!]!) {
  fileUpdate(files: $files) {
    files {
      id alt fileStatus
      ... on MediaImage { image { url altText width height } }
    }
    userErrors { field message code }
  }
}
```

The workhorse mutation for file management. `FileUpdateInput` supports:

- **Attach to product(s)**: `referencesToAdd: [productGid]`
- **Detach from product(s)**: `referencesToRemove: [productGid]` — file stays in Files library
- **Update alt text**: `alt: "..."`
- **Replace content**: `originalSource: <url>` (external URL or staged-upload URL)
- **Replace preview image**: `previewImageSource: <url>` (for videos/generic files)
- **Rename**: `filename: "..."`

BARS use: sold-out image swap = one `FileUpdate` call with `referencesToRemove: [productGid]` for the old file + a separate call with `referencesToAdd: [productGid]` for the sold-out file (or batch both into one `files: [...]` array).

Supersedes legacy `FileUpdateProductRef` (from `queries/media.py`) which already used `fileUpdate` — same underlying mutation, richer response. Also supersedes legacy `DeleteProductMedia` (which called deprecated `productDeleteMedia`) — modern detach uses `referencesToRemove`.

Callers to migrate later:
- `FileUpdateProductRef` — 0 known callers per prior grep
- `DeleteProductMedia` — 0 known callers per prior grep
