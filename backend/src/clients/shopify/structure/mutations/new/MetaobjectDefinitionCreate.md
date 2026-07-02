Status: keep (new — added 2026-07-01)
Resource: Metaobject
Path: backend/src/clients/shopify/queries/metaobject_definition_create.graphql
Generated: backend/src/clients/shopify/generated/metaobject_definition_create.py

```graphql
mutation MetaobjectDefinitionCreate($definition: MetaobjectDefinitionCreateInput!) {
  metaobjectDefinitionCreate(definition: $definition) {
    metaobjectDefinition {
      id type name description displayNameKey
      fieldDefinitions {
        key name required
        type { name category }
      }
    }
    userErrors { ...MetaobjectUserError }
  }
}
```

Fragments used: `MetaobjectUserError`.

Supersedes legacy inline `mutation CreateMetaobjectDefinition { metaobjectDefinitionCreate(definition: …) }` from `create_league_metaobject_definition.py:120`.

Callers to migrate later: `backend/lib/clients/shopify_client_old/create_league_metaobject_definition.py` (one-off script). Whether this script survives Phase 2 relocations is TBD — probably moves to `backend/scripts/shopify/` and switches to the new codegen client, OR is retired entirely if the metaobject definitions are now considered manually-managed via the Shopify admin UI.
