Status: superseded (2026-07-01) — new op `MetaobjectCreate` at `backend/src/clients/shopify/queries/metaobject_create.graphql`; tracker at `structure/mutations/new/MetaobjectCreate.md`
Resource: Metaobject
Path: backend/lib/clients/shopify_client_old/populate_league_metaobjects.py:488, 564 (inline f-string)
Replacement: **`MetaobjectCreate($metaobject: MetaobjectCreateInput!)`** — one op for both venue and league call sites; input payload differs.

`metaobjectCreate(metaobject: {type, fields, capabilities})` — two call sites
in the population script (venue and league). Same disposition as
`metaobjectDefinitionCreate`.
