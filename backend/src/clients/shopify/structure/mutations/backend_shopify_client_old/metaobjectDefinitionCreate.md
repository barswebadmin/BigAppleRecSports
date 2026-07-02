Status: superseded (2026-07-01) — new op `MetaobjectDefinitionCreate` at `backend/src/clients/shopify/queries/metaobject_definition_create.graphql`; tracker at `structure/mutations/new/MetaobjectDefinitionCreate.md`
Resource: Metaobject
Path: backend/lib/clients/shopify_client_old/create_league_metaobject_definition.py:120 (inline f-string)
Replacement: **`MetaobjectDefinitionCreate($definition: MetaobjectDefinitionCreateInput!)`**.

Inline mutation used by the one-shot league/venue definition creator. If the
creation script sticks around, promote to `.graphql` op
(`MetaobjectDefinitionCreate($definition: MetaobjectDefinitionCreateInput!)`);
otherwise let it die with the script.
