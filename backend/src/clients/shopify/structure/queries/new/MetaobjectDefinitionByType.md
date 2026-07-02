Status: keep (new — added 2026-07-01)
Resource: Metaobject
Path: backend/src/clients/shopify/queries/metaobject_definition_by_type.graphql
Generated: backend/src/clients/shopify/generated/metaobject_definition_by_type.py

```graphql
query MetaobjectDefinitionByType($type: String!) {
  metaobjectDefinitionByType(type: $type) {
    id type name description displayNameKey
    fieldDefinitions {
      key name required
      type { name category }
    }
  }
}
```

Fragments used: none (definition selection isn't shared with other ops yet — could extract `MetaobjectDefinition` fragment when the second consumer appears).

Supersedes legacy inline queries in `populate_league_metaobjects.py:353, 387` (which grabbed the definition by type before creating/looking up metaobjects).

Callers to migrate later: `populate_league_metaobjects.py`.
