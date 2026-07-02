Status: superseded (2026-07-01) — legacy called Shopify's `productDeleteMedia` which is now `@deprecated(reason: "Use fileUpdate instead.")` per the pinned 2026-07 schema
Resource: Media
Path: backend/lib/clients/shopify_client_old/queries/media.py → `DeleteProductMedia`
Replacement: two shapes depending on intent —
  - **detach only** (file stays in Files library): `FileUpdate({files: [{id: fileGid, referencesToRemove: [productGid]}]})` → `structure/mutations/new/FileUpdate.md`
  - **permanent delete** (nukes file from library, Shopify auto-removes product refs): `FileDelete({fileIds: [fileGid]})` → `structure/mutations/new/FileDelete.md`

Note: legacy op took **product-scoped media node IDs** (returned `deletedMediaIds` + `deletedProductImageIds`) while the modern ops take **File GIDs**. Caller migration may need a lookup step to translate media node IDs → File IDs if the caller doesn't already have the File GID.

```graphql
mutation deleteProductMedia($productId: ID!, $mediaIds: [ID!]!) {
  productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
    deletedMediaIds
    userErrors { field message }
  }
}
```
