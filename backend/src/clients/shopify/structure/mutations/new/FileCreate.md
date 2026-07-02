Status: keep (new — added 2026-07-01)
Resource: Media / File
Path: backend/src/clients/shopify/queries/file_create.graphql
Generated: backend/src/clients/shopify/generated/file_create.py (regenerate on next `just codegen-shopify`)

```graphql
mutation FileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files {
      id alt fileStatus
      ... on MediaImage { image { url altText width height } }
    }
    userErrors { field message code }
  }
}
```

Uploads new File(s) to the Files library. `FileCreateInput` requires `originalSource` (external URL or staged-upload URL); optionally set `filename`, `contentType`, `alt`, `duplicateResolutionMode`.

**Note**: `FileCreateInput` does NOT support attaching to a product at creation time. To upload-and-attach in one flow: (1) `FileCreate` the file, (2) `FileUpdate` with `referencesToAdd: [productGid]` to attach it. Or use `productUpdate(product: {id, media: [{originalSource, mediaContentType}]})` for the atomic per-product case.

Legacy equivalent: `AttachProductMedia` (called deprecated `productCreateMedia`) — new flow is `FileCreate` + `FileUpdate` (or `productUpdate.media`).

Callers to migrate later: none currently — legacy `AttachProductMedia` had no direct users found in earlier greps of the tracker.
