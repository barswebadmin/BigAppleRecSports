# shopify_gql

Typed Shopify Admin GraphQL client. Operations are hand-written `.graphql` files; [ariadne-codegen](https://github.com/mirumee/ariadne-codegen) materializes them into typed Python methods + pydantic result models.

## Layout

- `operations/` — hand-written queries/mutations, one op per file
- `schema/` — fetched Shopify SDL (committed; bump deliberately)
- `generated/` — codegen output (committed; reviewable in PRs)
- `*.py` at root — client class, exceptions, business-logic helpers
- `scripts/` — schema fetch + op scaffolder

## Fetch the schema

```bash
uv run python scripts/refresh_schema.py
```

Writes `schema/admin_<API_VERSION>.graphql`.

## Add an operation

1. Write a `.graphql` file in `operations/` (one op per file).
2. Run codegen:
   ```bash
   uv run ariadne-codegen
   ```
3. If the new op needs raise-on-userErrors semantics or domain shaping, add a wrapper method on `ShopifyClient` in `shopify_client.py`.

## Error handling — DIFFERENT from the old `shared_utilities` client

The wrappers on `ShopifyClient` (`update_product`, `update_variants`, `update_file`, `delete_file`, `add_inventory`, `remove_inventory`) **raise** `ShopifyUserError` on business-validation failures. They do NOT return `(data, errors)` tuples. Callers that need to forward errors to Slack (or any other surface) must change shape when migrating off the old client.

**Old client (still used by most lambdas + backend):**
```python
_, errors = client.update_product(product_id, title=new_title, tags=new_tags)
if errors:
    slack_notify(format_errors(errors))   # errors is list[dict]
```

**New client:**
```python
try:
    client.update_product(id=product_gid, title=new_title, tags=new_tags)
except ShopifyUserError as e:
    slack_notify(format_shopify_user_error(e))
```

(Callers never import `ProductUpdateInput` / `FileUpdateInput` / `ProductVariantsBulkInput`. The wrappers accept flat kwargs and construct the typed inputs internally — pydantic validates at construction.)

What's on a `ShopifyUserError` (use these to format the Slack payload):

| Attribute | Type | What it carries |
|---|---|---|
| `e.operation` | `str` | Mutation name, e.g. `"productUpdate"` |
| `e.user_errors` | `list[<codegen'd UserError>]` | One entry per individual rejection |
| `e.user_errors[i].code` | `Enum` (per-mutation) | Programmatic identifier — `INVALID_INPUT`, `CHANGE_FROM_QUANTITY_STALE`, `DOES_NOT_EXIST`, etc. |
| `e.user_errors[i].message` | `str` | Human-readable message — what to put in the Slack body |
| `e.user_errors[i].field` | `list[str] \| None` | Path to the offending field, e.g. `["input", "changes", "0", "changeFromQuantity"]` |
| `e.has_code("...")` | `bool` | Convenience for branching on a specific code (e.g. swallow vs alert) |
| `str(e)` | `str` | Pre-formatted `"<operation>: [CODE] msg (field=a.b)"` — useful as a fallback for a one-line Slack message |

Transport / system failures (auth expired, rate limit, 5xx, malformed query) raise a **different** exception — `GraphQLClientGraphQLMultiError` from ariadne. If your Slack notifier wants to distinguish "business rejection" from "system failure" (different severity, different channels, different runbook), catch the two separately:

```python
from shopify_gql.exceptions import ShopifyUserError
from shopify_gql.generated.exceptions import GraphQLClientGraphQLMultiError

try:
    client.update_product(product=...)
except ShopifyUserError as e:
    slack_notify_info(format_shopify_user_error(e))      # business — usually expected, sometimes
except GraphQLClientGraphQLMultiError as e:
    slack_notify_alert(format_transport_error(e))        # system — page someone
```

Queries (`get_product`, `find_products`, `get_customers`, …) have no `userErrors` channel at all — they either return data or raise a transport error. No `try: ... except ShopifyUserError` needed around queries.
