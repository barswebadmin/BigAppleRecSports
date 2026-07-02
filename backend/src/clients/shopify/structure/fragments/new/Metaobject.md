Status: keep (new — added 2026-07-01)
Path: backend/src/clients/shopify/queries/fragments/metaobject.graphql
Generated: `Metaobject` in `generated/fragments.py`

```graphql
fragment Metaobject on Metaobject {
  id
  handle
  type
  displayName
  updatedAt
  fields { key type value }
}
```

Composes: nothing (leaf).

Used by: `MetaobjectCreate` (return payload), `FindMetaobjects` (list nodes), `Product` fragment (`importantDates.reference` inline `... on Metaobject` — refactored 2026-07-01 to spread `...Metaobject` instead of inlining the same `fields{key,type,value}` selection).

Selection tuned to what the league-metaobject population scripts need. Extend if a new caller needs richer capabilities/access/definition info.
