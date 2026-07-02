Status: retired (2026-07-01) — deleted with the parent dir
Old path: `lib/clients/shopify-client/pyproject.toml` (dir gone)

## What became of each dep

- `gql[httpx]==4.0.0` — **dropped from `backend/pyproject.toml`**. Was only used by `shop_client.py`'s `DSLSchema` + `HTTPXTransport`. Codegen client uses `httpx` directly.
- `graphql-core==3.2.11` — **dropped from `backend/pyproject.toml`** as a runtime pin. Reintroduced in **root pyproject `[dependency-groups] dev`** as `graphql-core>=3.2.7,<3.3` (transitive via ariadne-codegen, declared for clarity). Codegen-time dep; not shipped at runtime.
- `python-box>=7.0.0` — kept in `backend/pyproject.toml`. Used by codegen client + potentially elsewhere in backend.
- `python-dotenv>=1.0.0` — already in backend runtime deps.

## Package config that dies with the dir

- `[build-system]` + hatchling wheel target — the dir wasn't a package anymore once its content was retired.
- `[tool.hatch.build.targets.wheel]` — irrelevant post-retirement.

## Deployment linkage

The AWS Lambda layer at `aws/lambda/layers/lib/shopify-client` was a symlink into this now-deleted dir. User is retiring most Lambdas; broken layer symlinks are out of scope.
