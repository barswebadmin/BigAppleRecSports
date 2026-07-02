Status: keep (new — added 2026-07-01)
Resource: Media
Path: backend/src/clients/shopify/queries/get_media_image.graphql
Generated: backend/src/clients/shopify/generated/get_media_image.py (regenerate on next `just codegen-shopify`)

```graphql
query GetMediaImage($id: ID!) {
  node(id: $id) {
    ... on MediaImage {
      id alt status mediaContentType
      image { url altText width height }
    }
  }
}
```

Uses `node(id:)` interface pattern — no direct `mediaImage(id:)` root query in the Shopify schema. Callers pass a MediaImage GID (`gid://shopify/MediaImage/…`) and destructure via the `... on MediaImage` inline fragment in the codegen result.

Supersedes legacy `GetMediaImageUrl` (from `queries/media.py`) — new op returns richer info (alt, status, dimensions) rather than just URL.

Callers to migrate later: legacy import path `from lib.clients.shopify_client_old.queries.media import GetMediaImageUrl`. Custom `parse_response` in the legacy returned the URL string directly ("MediaImage not found or has no URL"); new op returns the typed pydantic result — extract `.node.image.url` at call site.
