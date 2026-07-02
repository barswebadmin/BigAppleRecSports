Status: superseded
Path: backend/lib/clients/shopify_client_old/shopify_schema.py
      backend/lib/clients/shopify_client_old/shopify_schema_filtered.py

sgqlc-typed full-schema modules — the predecessor of ariadne codegen. Contains
scalars (`ARN`, `BigInt`) plus every enum and type in the Shopify admin schema.

Nothing in the new client uses these. Delete once we confirm no residual
callers.
