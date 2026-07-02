Status: superseded (2026-07-01) — new op `MetaobjectDefinitionByType` at `backend/src/clients/shopify/queries/metaobject_definition_by_type.graphql`; tracker at `structure/queries/new/MetaobjectDefinitionByType.md`
Resource: Metaobject
Path: backend/lib/clients/shopify_client_old/populate_league_metaobjects.py:353, 387 (inline f-string query)
Replacement: **`MetaobjectDefinitionByType($type: String!)`**. Population script (if it survives Phase 2 to `backend/scripts/shopify/`) uses the new op via typed codegen client.

Ad-hoc `metaobjectDefinitionByType(type: "$LEAGUE_TYPE")` lookup used by the
league-metaobject population script. Same pattern also queries
`metaobjectDefinitionByType(type: "$VENUE_TYPE")`.

Decide: if the population scripts survive the consolidation, promote to a
proper `.graphql` op (`MetaobjectDefinitionByType($type: String!)`); if the
scripts move out of the client dir, keep the inline GQL with them.
