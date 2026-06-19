"""Export orders query with full line item and custom attribute details."""

import requests

from shared_utilities.clients.shopify_client.gql import GqlQuery, GqlResult


class GetAllOrdersForExport(GqlQuery):
    """Fetch all orders with line items, customer data, and custom attributes.
    
    Optimized for export with product handles to enable filtering by sport.
    """
    
    query = """
query getAllOrdersForExport($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query, sortKey: CREATED_AT, reverse: true) {
    nodes {
      id
      name
      legacyResourceId
      createdAt
      updatedAt
      displayFinancialStatus
      displayFulfillmentStatus
      totalPriceSet { shopMoney { amount currencyCode } }
      currentTotalPriceSet { shopMoney { amount currencyCode } }
      currentTotalDiscountsSet { shopMoney { amount currencyCode } }
      customAttributes { key value }
      customer {
        id
        legacyResourceId
        email
        firstName
        lastName
      }
      lineItems(first: 10) {
        nodes {
          id
          name
          title
          quantity
          originalUnitPriceSet { shopMoney { amount currencyCode } }
          discountedUnitPriceSet { shopMoney { amount currencyCode } }
          totalDiscountSet { shopMoney { amount currencyCode } }
          customAttributes { key value }
          variant {
            id
            legacyResourceId
            title
            sku
          }
          product {
            id
            legacyResourceId
            handle
            title
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""
    data_key = "orders"
    errors_key = None
    result_key = None

    def build_query(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        *,
        first: int = 100,
        after: str | None = None,
        created_at_min: str | None = None,
        created_at_max: str | None = None,
    ) -> tuple[str, dict]:
        """Build query with optional date filtering.
        
        Args:
            first: Number of orders per page (max 250)
            after: Cursor for pagination
            created_at_min: ISO 8601 date string (e.g., "2025-03-15T00:00:00Z")
            created_at_max: ISO 8601 date string
        
        Returns:
            (query_string, variables_dict)
        """
        query_parts = []
        
        if created_at_min:
            query_parts.append(f"created_at:>={created_at_min}")
        if created_at_max:
            query_parts.append(f"created_at:<={created_at_max}")
        
        query_str = " AND ".join(query_parts) if query_parts else ""
        
        variables: dict = {"first": first}
        if query_str:
            variables["query"] = query_str
        if after:
            variables["after"] = after
        
        return self.query, variables

    def parse_response(self, response: requests.Response) -> GqlResult:
        data, errors = super().parse_response(response)
        if errors:
            return None, errors
        return data, None
