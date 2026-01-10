"""
TODO: Either refactor to use sgqlc/ShopifySGQLCClient or delete if not needed.

This function provides cursor-based pagination for fetching all customers.
It uses the old GraphQL request pattern and should be refactored to use
the modern ShopifyService with sgqlc models, or removed if not needed.
"""

# TODO: Either refactor to use sgqlc/ShopifySGQLCClient or delete if not needed
# def get_all_customers_paginated(
#     config: Dict[str, Any],
#     query: Optional[str] = None,
#     page_size: int = 250
# ) -> List[Customer]:
#     """
#     Fetch all customers using cursor-based pagination.
#     
#     Useful for large result sets that need to be fetched in chunks.
#     
#     Args:
#         config: Shopify API configuration
#         query: Optional search query (e.g., "email:test@example.com")
#         page_size: Number of customers per page (default: 250, max recommended: 250)
#         
#     Returns:
#         List of all Customer objects
#         
#     Example:
#         ```python
#         # Get all customers
#         all_customers = get_all_customers_paginated(config)
#         
#         # Get all customers matching a query
#         all_test_customers = get_all_customers_paginated(
#             config, 
#             query="email:*@test.com"
#         )
#         ```
#     """
#     all_customers: List[Customer] = []
#     cursor: Optional[str] = None
#     page_num = 1
#     
#     base_query = """
#     query getCustomers($query: String, $after: String, $first: Int!) {
#         customers(first: $first, query: $query, after: $after) {
#             edges {
#                 cursor
#                 node {
#                     id
#                     firstName
#                     lastName
#                     email
#                     displayName
#                     phone
#                     tags
#                     numberOfOrders
#                     createdAt
#                     updatedAt
#                     state
#                     verifiedEmail
#                     addresses {
#                         address1
#                         address2
#                         city
#                         province
#                         zip
#                         country
#                     }
#                     defaultAddress {
#                         address1
#                         address2
#                         city
#                         province
#                         zip
#                         country
#                     }
#                 }
#             }
#             pageInfo {
#                 hasNextPage
#                 hasPreviousPage
#                 startCursor
#                 endCursor
#             }
#         }
#     }
#     """
#     
#     while True:
#         payload = {
#             "query": base_query,
#             "variables": {
#                 "query": query,
#                 "after": cursor,
#                 "first": page_size
#             }
#         }
#         
#         try:
#             response = make_graphql_request(payload, config)
#             
#             if "error" in response or "errors" in response:
#                 error_msg = response.get("error") or response.get("errors", [])
#                 raise Exception(f"GraphQL error on page {page_num}: {error_msg}")
#             
#             customers_data = response.get("data", {}).get("customers", {})
#             
#             # Use Customers list model - automatically handles Connection structure resolution
#             if customers_data:
#                 if Customers is None:
#                     raise Exception("Customers list model not available")
#                 page_customers = Customers(customers_data)
#                 all_customers.extend(page_customers)
#             
#             page_info_data = customers_data.get("pageInfo", {}) if isinstance(customers_data, dict) else {}
#             
#             has_next = page_info_data.get("hasNextPage", False)
#             cursor = page_info_data.get("endCursor")
#             
#             if not has_next or not cursor:
#                 break
#             
#             page_num += 1
#             
#         except Exception as e:
#             raise Exception(f"Error fetching page {page_num}: {str(e)}")
#     
#     return all_customers

