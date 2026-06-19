"""Order-related GraphQL queries."""

import requests

from shared_utilities.clients.shopify_client.gql import GqlQuery, GqlResult


class GetOrdersByProduct(GqlQuery):
    query = """
query getOrdersByProduct($query: String!, $first: Int!, $after: String) {
  orders(first: $first, after: $after, query: $query) {
    nodes {
      id name createdAt cancelledAt totalPriceSet { shopMoney { amount currencyCode } }
      customer { id email firstName lastName tags }
      customAttributes { key value }
      lineItems(first: 250) {
        nodes {
          id title quantity
          customAttributes { key value }
          variant { id title }
          product { id }
        }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""
    data_key = "orders"
    errors_key = None
    result_key = None

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        *,
        product_id: str | int,
        first: int = 100,
        after: str | None = None,
        created_at_min: str | None = None,
        created_at_max: str | None = None,
    ) -> tuple[str, dict]:
        query_parts = [f"product_id:{product_id}"]
        if created_at_min:
            query_parts.append(f"created_at:>={created_at_min}")
        if created_at_max:
            query_parts.append(f"created_at:<={created_at_max}")

        query_str = " AND ".join(query_parts)
        variables: dict = {"query": query_str, "first": first}
        if after:
            variables["after"] = after

        return self.query, variables

    def parse_response(self, response: requests.Response) -> GqlResult:
        data, errors = super().parse_response(response)
        if errors:
            return None, errors
        return data, None
