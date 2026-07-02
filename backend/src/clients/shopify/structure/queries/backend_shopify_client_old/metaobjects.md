Status: superseded (2026-07-01) — new op `FindMetaobjects` at `backend/src/clients/shopify/queries/find_metaobjects.graphql`; tracker at `structure/queries/new/FindMetaobjects.md`
Resource: Metaobject
Path: backend/lib/clients/shopify_client_old/populate_league_metaobjects.py:438 (inline f-string)
Replacement: **`FindMetaobjects($type: String!, $first: Int!, $after: String, $query: String, $sortKey: String)`** — supports the same `type` filter plus optional Shopify search-query + sort.

`metaobjects(type: …, first: …)` listing lookup used to check for existing
venue metaobjects before creating a new one. Same disposition as
`metaobjectDefinitionByType`.
