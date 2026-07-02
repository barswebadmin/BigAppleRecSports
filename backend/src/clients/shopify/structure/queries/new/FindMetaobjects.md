Status: keep (new — added 2026-07-01)
Resource: Metaobject
Path: backend/src/clients/shopify/queries/find_metaobjects.graphql
Generated: backend/src/clients/shopify/generated/find_metaobjects.py

```graphql
query FindMetaobjects(
  $type: String!, $first: Int!, $after: String,
  $query: String, $sortKey: String
) {
  metaobjects(type: $type, first: $first, after: $after, query: $query, sortKey: $sortKey) {
    nodes { ...Metaobject }
    pageInfo { ...PageInfo }
  }
}
```

Fragments used: `Metaobject`, `PageInfo`.

Search-form op — pair to direct-lookup ops if we ever need `GetMetaobject($id: ID!)` later.

Root `Query.metaobjects` takes `type: String!` required (per the pinned 2026-07 schema) plus optional `query` (supports `fields.{key}:{value}` filters, `handle`, `id` range, `updated_at`, `display_name`) and `sortKey` (`id`, `type`, `updated_at`, `display_name`). Wired all through so callers can filter/sort as needed.

Supersedes legacy inline `metaobjects(type: "$LEAGUE_TYPE", first: …)` query in `populate_league_metaobjects.py:438` (checked for existing venue metaobjects before creating new ones).

Callers to migrate later: `populate_league_metaobjects.py`.
