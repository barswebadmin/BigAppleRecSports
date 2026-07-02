Status: drop (fold into `ProductUpdate`)
Resource: Product / Metafield
Path: backend/lib/clients/shopify_client_old/populate_league_metaobjects.py:619 (inline f-string)

Inline `productUpdate(input: {id, metafields: [{namespace,key,type,value}]})`
that links a metaobject to a product via a metafield reference. Same op as
`ProductUpdate` — pass `metafields` under `ProductUpdateInput` and this
becomes a call-site variation, not a separate op.
