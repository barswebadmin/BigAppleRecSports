Status: superseded (2026-07-01) — new op `GetMediaImage` at `backend/src/clients/shopify/queries/get_media_image.graphql`; tracker at `structure/queries/new/GetMediaImage.md`
Resource: Media
Path: backend/lib/clients/shopify_client_old/queries/media.py → `GetMediaImageUrl`
Replacement: **`GetMediaImage($id: ID!)`** — same `node(id:)` pattern, richer selection (alt, status, dimensions), typed pydantic response

```graphql
query getMediaImageUrl($id: ID!) {
  node(id: $id) { ... on MediaImage { image { url } } }
}
```

Custom `parse_response` returns "MediaImage not found or has no URL" when
image or url missing — replicate at call site.
