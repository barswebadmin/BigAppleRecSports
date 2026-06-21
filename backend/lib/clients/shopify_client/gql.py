"""GraphQL query base class, result type, and GID helper."""

from typing import Any

import requests

GqlResult = tuple[dict[str, Any] | None, list[dict] | None]


def build_shopify_gid(resource_type: str, id_value: str | int) -> str:
    """Build a Shopify GID from a resource type and numeric or string ID.

    resource_type accepts singular PascalCase: "Product", "ProductVariant", etc.
    id_value may be a bare numeric ID or any slash-delimited string (GID or URL).
    """
    id_slug = str(id_value).rsplit("/", maxsplit=1)[-1]
    return f"gid://shopify/{resource_type}/{id_slug}"


class GqlQuery:
    """Base class for Shopify GraphQL query/mutation descriptors.

    Subclasses define:
        - query:       GQL string
        - data_key:    top-level key in response `data`
        - errors_key:  key under data_key for userErrors (None for read queries)
        - result_key:  key under data_key for the payload (None = return data_key node)
    """

    query: str
    data_key: str
    errors_key: str | None = "userErrors"
    result_key: str | None = None

    def build_query(self, **kwargs: Any) -> tuple[str, dict]:
        raise NotImplementedError

    def parse_response(self, response: requests.Response) -> GqlResult:
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            return None, [{"message": str(e)}]

        try:
            body = response.json()
        except ValueError as e:
            return None, [{"message": f"Failed to decode JSON: {e}"}]

        top_errors = body.get("errors")
        if top_errors:
            return None, top_errors

        data = body.get("data", {})
        node = data.get(self.data_key)

        if self.errors_key:
            user_errors = (node or {}).get(self.errors_key, [])
            if user_errors:
                return None, user_errors

        if node is None:
            return None, [{"message": f"No data returned for key '{self.data_key}'"}]

        payload = node[self.result_key] if self.result_key else node
        return payload, None
