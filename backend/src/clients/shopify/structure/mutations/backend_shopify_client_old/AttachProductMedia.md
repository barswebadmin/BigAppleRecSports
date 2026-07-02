Status: superseded (2026-07-01) — legacy called Shopify's `productCreateMedia` which is now `@deprecated(reason: "Use productUpdate or productSet instead.")` per the pinned 2026-07 schema
Resource: Media
Path: backend/lib/clients/shopify_client_old/queries/media.py → `AttachProductMedia`
Replacement: two-step modern flow — **`FileCreate({files: [{originalSource, contentType}]})`** to upload the file, then **`FileUpdate({files: [{id: fileGid, referencesToAdd: [productGid]}]})`** to attach it to a product. Or the atomic single-product form via `ProductUpdate(product: {id, media: [{originalSource, mediaContentType}]})`. Trackers: `structure/mutations/new/FileCreate.md` + `FileUpdate.md`.

```graphql
mutation attachProductMedia($productId: ID!, $media: [CreateMediaInput!]!) {
  productCreateMedia(productId: $productId, media: $media) {
    media { id }
    userErrors { field message }
  }
}
```

Helper builds `{mediaContentType: IMAGE, originalSource: <url>}` — keep at call
site.
