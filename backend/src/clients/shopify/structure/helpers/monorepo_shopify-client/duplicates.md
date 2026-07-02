Status: keep (this dir is the survivor for the shell/curl triplication)
Delete: n/a for this dir; see A2 for the deletion of the backend copies
Path: `lib/clients/shopify-client/`

Files here that are byte-identical (`shasum`) to files elsewhere:

| File | Also lives at | Survivor |
|---|---|---|
| `aws_add_inventory_to_variant.sh` | `backend/.../shopify_client_old/aws_add_inventory_to_variant.sh` | **this dir** (A2 survivor) |
| `aws_move-inv.sh` | `backend/.../shopify_client_old/aws_move-inv.sh` | **this dir** (A2 survivor) |
| `shopify-requests.curl` | `backend/.../shopify_client_old/shopify-requests.curl` | **this dir** (A2 survivor) |
| `schema_filter_config.json` | `backend/src/clients/shopify/schema_filter_config.json` | **`backend/src/clients/shopify/`** — the ariadne-codegen target dir |

`schema_filter_config.json` here is a stray copy; delete this one, keep the
one in `backend/src/clients/shopify/`.

`uv.lock` is unique to this package; belongs with `pyproject.toml`. Merges
with the unified `shopify/pyproject.toml` later.

Blocked on: grep for callers of these shell scripts (unlikely but confirm).
