Status: keep — refactored 2026-07-01 to compose `ProductVariant` and `Metaobject` fragments (previously inlined both selections)
Target: backend/src/clients/shopify/queries/fragments/product.graphql
Generated model: `Product` (+ nested subclasses) in `generated/fragments.py`

# Product fragment

Composes:
- `ProductVariant` — via `variants(first: 5) { nodes { ...ProductVariant } }` → codegen surfaces subclass reuse (`ProductVariantsNodes(ProductVariant): pass`).
- `Metaobject` — via `importantDates.reference { ... on Metaobject { ...Metaobject } }`.

Selection set (grouped):
- Scalars: `id`, `title`, `handle`, `descriptionHtml`, `status`, `tags`, `totalInventory`, `createdAt`, `updatedAt`
- Metafield: `importantDates: metafield(namespace: "custom", key: "important_dates").reference { ... on Metaobject { ...Metaobject } }`
- Variants: `variants(first: 5).nodes { ...ProductVariant }`
- Media: `media(first: 10).nodes { id }` — minimal; extend if a caller needs richer media info
- Publications: `publications: resourcePublicationsV2(first: 10).nodes { isPublished, publication.name }`

Composed into: `FindProducts`, `GetProduct`, `ProductUpdate`.
