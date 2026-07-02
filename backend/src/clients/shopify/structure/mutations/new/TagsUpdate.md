Status: keep
Resource: Tags (any Node)
Path: backend/src/clients/shopify/queries/tags_update.graphql
Generated: shopify/generated/tags_update.py

```graphql
mutation TagsUpdate($gid: ID!, $tagsToAdd: [String!]!, $tagsToRemove: [String!]!) {
  added:   tagsAdd(id: $gid, tags: $tagsToAdd)    { node { id } userErrors { field message } }
  removed: tagsRemove(id: $gid, tags: $tagsToRemove) { node { id } userErrors { field message } }
}
```

Aliased dual mutation. Node-agnostic (customer, product, order, …). Overlaps
with `CustomerUpdate` for the customer case — keep both; `TagsUpdate` is the
right tool when you don't want to fetch/return the whole entity.
