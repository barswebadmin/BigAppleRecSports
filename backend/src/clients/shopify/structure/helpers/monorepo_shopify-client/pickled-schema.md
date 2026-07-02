Status: retired (2026-07-01) — deleted from repo
Old paths (all now gone):
- `lib/clients/shopify-client/2026-07.graphql.pickle`
- `backend/lib/clients/shopify-client/2026-07.graphql.pickle`
- `backend/src/clients/shopify/2026-07.graphql.pickle`

## Why retired

The 19 MB pickled `graphql.GraphQLSchema` served only `shop_client.py`'s DSL runtime (dynamic query construction via `DSLSchema(schema)`). With `shop_client.py` retired, nothing loads the pickle anymore.

Ariadne-codegen reads `schema.graphql` (SDL, ~3.5 MB) at codegen time — never the pickle. Runtime uses baked-in query strings + pydantic models from the generated modules.

## Regeneration if ever needed

If a future use case wants dynamic schema introspection (e.g. a one-off script that constructs queries at runtime), regenerate the pickle from the SDL as a `backend/scripts/` step:

```python
from graphql import build_ast_schema, parse
import pickle
with open("backend/src/clients/shopify/schema.graphql") as f:
    sdl = f.read()
schema = build_ast_schema(parse(sdl))
with open("YYYY-MM.graphql.pickle", "wb") as f:
    pickle.dump(schema, f)
```

Not a runtime concern; not part of the backend deployable.

## Path-arithmetic violation goes away by deletion

`shop_client.py:82` had `PICKLE_PATH = <__file__-relative>` — that whole violation retires with the file. No fix needed; the code doesn't exist anymore.
