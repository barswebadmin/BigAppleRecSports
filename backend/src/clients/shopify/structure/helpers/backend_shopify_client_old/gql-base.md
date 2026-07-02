Status: drop (superseded)
Path: backend/lib/clients/shopify_client_old/gql.py

Legacy raw-string GraphQL runner:
- `GqlResult = tuple[dict | None, list[dict] | None]`
- `class GqlQuery` — base for the `queries/*.py` op descriptors (query str,
  data_key, errors_key, result_key, `build_query`, `parse_response`)
- `build_shopify_gid(resource_type, id_value)` — see `build_shopify_gid.md`

The `GqlQuery` machinery is replaced by codegen's generated client. Only
`build_shopify_gid` survives (tracked separately).
