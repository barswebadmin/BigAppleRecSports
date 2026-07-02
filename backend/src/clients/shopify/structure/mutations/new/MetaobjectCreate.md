Status: keep (new — added 2026-07-01)
Resource: Metaobject
Path: backend/src/clients/shopify/queries/metaobject_create.graphql
Generated: backend/src/clients/shopify/generated/metaobject_create.py

```graphql
mutation MetaobjectCreate($metaobject: MetaobjectCreateInput!) {
  metaobjectCreate(metaobject: $metaobject) {
    metaobject { ...Metaobject }
    userErrors { ...MetaobjectUserError }
  }
}
```

Fragments used: `Metaobject`, `MetaobjectUserError`.

Supersedes legacy inline `mutation { metaobjectCreate(metaobject: …) }` calls in `populate_league_metaobjects.py:488, 564` — one for venue metaobjects, one for league metaobjects. Both become the same op with different `MetaobjectCreateInput` payloads at the call site.

Callers to migrate later: `populate_league_metaobjects.py`.
