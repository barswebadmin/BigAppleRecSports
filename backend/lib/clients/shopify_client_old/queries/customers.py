"""Customer-related GraphQL queries and mutations."""

from typing import Any, cast

import requests

from shared_utilities.clients.shopify_client.gql import (
    GqlQuery,
    GqlResult,
    build_shopify_gid,
)


class GetCustomer(GqlQuery):
    query = """
query getCustomer($id: ID!) {
  customer(id: $id) {
    id email tags
  }
}
"""
    data_key = "customer"

    def build_query(self, *, customer_id: str | int) -> tuple[str, dict]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.query, {
            "id": build_shopify_gid("Customer", customer_id),
        }


class SearchCustomerByEmail(GqlQuery):
    query = """
query searchCustomer($query: String!) {
  customers(first: 1, query: $query) {
    nodes { id email tags }
  }
}
"""
    data_key = "customers"

    def build_query(self, *, email: str) -> tuple[str, dict]:  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.query, {"query": f"email:{email}"}

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
        if not node:
            return None, [
                {"message": f"No data returned for key '{self.data_key}'"}
            ]

        nodes = node.get("nodes", [])
        if not nodes:
            return None, [{"message": "Customer not found"}]

        return nodes[0], None


class SearchCustomersByEmails(GqlQuery):
    query = """
query searchCustomers($query: String!, $first: Int!) {
  customers(first: $first, query: $query) {
    edges {
      node {
        id email tags
      }
    }
  }
}
"""
    data_key = "customers"

    def build_query(self, *, emails: list[str]) -> tuple[str, dict]:  # pyright: ignore[reportIncompatibleMethodOverride]
        email_clauses = " OR ".join(f'email:"{email}"' for email in emails)
        return self.query, {"query": email_clauses, "first": len(emails)}

    def parse_response(self, response: requests.Response) -> GqlResult:
        data, errors = super().parse_response(response)
        if errors or data is None:
            return None, errors
        nodes = data.get("edges", [])
        return cast(GqlResult, ([edge["node"] for edge in nodes], None))


class UpdateCustomerTags(GqlQuery):
    query = """
mutation updateCustomerTags($input: CustomerInput!) {
  customerUpdate(input: $input) {
    customer { id tags }
    userErrors { field message }
  }
}
"""
    data_key = "customerUpdate"
    errors_key = "userErrors"
    result_key = "customer"

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, *, customer_id: str | int, tags: list[str]
    ) -> tuple[str, dict]:
        return self.query, {
            "input": {
                "id": build_shopify_gid("Customer", customer_id),
                "tags": tags,
            }
        }
