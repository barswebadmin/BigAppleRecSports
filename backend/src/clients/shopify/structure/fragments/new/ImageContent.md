Status: keep (new — added 2026-07-01 for DRY pass)
Path: backend/src/clients/shopify/queries/fragments/image_content.graphql
Generated: `ImageContent` in `generated/fragments.py`

```graphql
fragment ImageContent on Image {
  url
  altText
  width
  height
}
```

Composes: nothing (leaf).

Used by: `GetMediaImage`, `FileCreate`, `FileUpdate` — every MediaImage-typed `image` field spreads it.

Named `ImageContent` (not just `Image`) to keep the codegen class name descriptive — the Shopify `Image` type is a common name and clashes with pydantic model naming from other libs at the call site.
