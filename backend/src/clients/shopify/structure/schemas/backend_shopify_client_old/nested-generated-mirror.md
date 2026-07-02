Status: drop
Path: backend/lib/clients/shopify_client_old/shopify/generated/**

Byte-identical mirror of `shopify/generated/**`. This is what Stage 2
eliminates — repoint ariadne codegen output at `shopify/generated/` (already
its target) and delete this entire nested tree along with
`shopify_client_old/shopify/{queries,schema.graphql,ariadne-codegen.toml,shopify_client.py,client_base.py,exceptions.py}`.
