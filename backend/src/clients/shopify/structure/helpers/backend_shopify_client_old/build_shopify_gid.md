Status: keep (relocate)
Path: backend/lib/clients/shopify_client_old/gql.py → `build_shopify_gid`
Target: backend/src/clients/shopify/gid.py (or fold into `urls.py` alongside `extract_shopify_id`)

```python
def build_shopify_gid(resource_type: str, id_value: str | int) -> str:
    id_slug = str(id_value).rsplit("/", maxsplit=1)[-1]
    return f"gid://shopify/{resource_type}/{id_slug}"
```

Pairs naturally with `extract_shopify_id` from `shopify_url_builder.py` — they
are inverse ops. Consider a single `gid.py` module exposing both.
