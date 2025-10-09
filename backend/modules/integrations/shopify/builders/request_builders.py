from typing import Dict, Any, List, Union, Optional, Set, Tuple

from .shopify_query_builders import build_product_gid
from modules.orders.models import FetchOrderRequest
from modules.products.models import FetchProductRequest

# from ..models.graphql_allowlist import (
#     derive_allowed_paths,
#     convert_paths_python_to_graphql,
#     derive_leaf_paths,
#     derive_scalar_leaf_paths,
# )
from ..models.orders import Order as OrderModel

# ---------------------------------------------------------------------------
# Generic, composable GraphQL selection helpers (mini-DSL)
# ---------------------------------------------------------------------------
# FieldSpec = Union[str, Dict[str, Union["FieldSpec", List["FieldSpec"]]], List["FieldSpec"]]


# def render_selection(spec: FieldSpec) -> str:
#     if isinstance(spec, str):
#         return spec
#     if isinstance(spec, list):
#         return " ".join(render_selection(s) for s in spec)
#     parts: List[str] = []
#     for key, val in spec.items():
#         if isinstance(val, list):
#             # Empty list means scalar leaf field: render without braces
#             if len(val) == 0:
#                 parts.append(key)
#             else:
#                 parts.append(f"{key} {{ {render_selection(val)} }}")
#         else:
#             # Nested object selection
#             inner = render_selection(val)
#             parts.append(f"{key} {{ {inner} }}")
#     return " ".join(parts)


# def build_return_fields(kind: str, base: str, selection: FieldSpec) -> str:
#     inner = render_selection(selection)
#     return f"{kind} {base} {{ {inner} }} }}"


# def _validate_path(path: str, tree) -> bool:
#     parts = path.split(".")
#     node = tree
#     for p in parts:
#         if isinstance(node, set):
#             if p not in node:
#                 return False
#             node = set()  # leaf
#         elif isinstance(node, dict):
#             if p not in node:
#                 return False
#             node = node[p]
#         else:
#             return False
#     return True


# def _paths_to_fields(paths: List[str]) -> FieldSpec:
#     # Build nested dict from dot paths
#     root: Dict[str, Any] = {}
#     for path in paths:
#         parts = path.split(".")
#         cur = root
#         for i, part in enumerate(parts):
#             if i == len(parts) - 1:
#                 cur.setdefault(part, [])
#             else:
#                 cur = cur.setdefault(part, {})
#     # Convert leaves with [] into simple scalar listing
#     def collapse(node):
#         if isinstance(node, dict):
#             out = {}
#             for k, v in node.items():
#                 out[k] = collapse(v)
#             return out
#         return []
#     return collapse(root)


# def _build_search_variable(req: FetchOrderRequest) -> Dict[str, Any]:
#     if req.order_id:
#         return {"q": f"id:{req.order_id}"}
#     if req.order_number:
#         return {"q": f"name:#{req.order_number}"}
#     if req.email:
#         return {"q": f"email:{req.email}"}
#     raise ValueError("Must provide order_id, order_number, or email")


# def _derive_allowlist_and_leaves() -> Tuple[Set[str], List[str]]:
#     allowed = derive_allowed_paths(OrderModel)
#     scalar_leaves = derive_scalar_leaf_paths(OrderModel)
#     return allowed, scalar_leaves


# def _gather_requested_python_paths(
#     selection_paths: Optional[List[str]], extra_paths: Optional[List[str]]
# ) -> List[str]:
#     requested: List[str] = []
#     if selection_paths:
#         requested.extend(selection_paths)
#     if extra_paths:
#         requested.extend(extra_paths)
#     return requested


# def _convert_and_validate_paths(
#     requested_py: List[str], allowed: Set[str]
# ) -> List[str]:
#     if not requested_py:
#         return []
#     requested_gql = convert_paths_python_to_graphql(OrderModel, requested_py)
#     invalid = [p for p in requested_gql if p not in allowed]
#     if invalid:
#         raise ValueError(f"Invalid selection paths: {invalid}")
#     return requested_gql


# def _expand_to_scalar_leaves(
#     requested_gql: List[str], scalar_leaves: List[str]
# ) -> List[str]:
#     if not requested_gql:
#         return scalar_leaves
#     expanded: List[str] = []
#     for p in requested_gql:
#         if p in scalar_leaves:
#             expanded.append(p)
#         else:
#             prefix = f"{p}."
#             expanded.extend([leaf for leaf in scalar_leaves if leaf.startswith(prefix)])
#     return sorted(set(expanded))


def build_order_fetch_request_payload(
    req: FetchOrderRequest,
    # *,
    # preset: str = "full",
    # selection_paths: Optional[List[str]] = None,
    # extra_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Build order fetch payload using composable selection renderer.
    Accepts FetchOrderRequest (digits-only) and returns {"query","variables"}.
    """
    # variables = _build_search_variable(req)
    # allowed, scalar_leaves = _derive_allowlist_and_leaves()

    # # Default selection to match curated shape if none provided
    # if not selection_paths and not extra_paths:
    #     selection_paths = [
    #         "id",
    #         "name",
    #         "total_price_set.shop_money.amount",
    #         "total_price_set.shop_money.currency_code",
    #         "customer.id",
    #         "customer.email",
    #         "transactions.id",
    #         "transactions.kind",
    #         "transactions.gateway",
    #         "transactions.parent_transaction.id",
    #         "refunds.created_at",
    #         "refunds.staff_member.first_name",
    #         "refunds.staff_member.last_name",
    #         "refunds.total_refunded_set.presentment_money.amount",
    #         "refunds.total_refunded_set.presentment_money.currency_code",
    #         "refunds.total_refunded_set.shop_money.amount",
    #         "refunds.total_refunded_set.shop_money.currency_code",
    #         "cancelled_at",
    #     ]

    # requested_py = _gather_requested_python_paths(selection_paths, extra_paths)
    # requested_gql = _convert_and_validate_paths(requested_py, allowed)
    # final_leaf_paths = _expand_to_scalar_leaves(requested_gql, scalar_leaves)

    # node_selection = _paths_to_fields(final_leaf_paths)
    # selection: FieldSpec = {"edges": {"node": node_selection}}
    # base = "FetchOrder($q: String!) { orders(first: 1, query: $q)"
    # query = build_return_fields("query", base, selection)
    search_query = "query { orders(first: 10, identifier: $identifier)"
    return_fields = "{ id name totalPriceSet {shopMoney {amount currencyCode} } customer {id email} transactions {id kind gateway parentTransaction {id} } refunds {createdAt staffMember {firstName lastName} totalRefundedSet {presentmentMoney {amount currencyCode} shopMoney {amount currencyCode} } } cancelledAt }"
    
    query = f"query {search_query} {return_fields}"
    if req.order_id:
        variables = { "identifier": { "id": req.order_id } }
    elif req.order_number:
        variables = { "identifier": { "name": req.order_number } }
    elif req.email:
        variables = { "identifier": { "email": req.email } }
    else:
        raise ValueError("Must provide order_id, order_number, or email")

    return {"query": query, "variables": variables}

def build_product_fetch_request_payload(
    req: FetchProductRequest,
) -> Dict[str, Any]:
    """
    Build product fetch payload using composable selection renderer.
    Accepts FetchProductRequest (digits-only) and returns {"query","variables"}.
    """
    
    search_query = "($identifier: ProductIdentifierInput!) { product: productByIdentifier(identifier: $identifier)"
    return_fields = "{ id handle title tags variants(first:10) {edges {node {id title inventoryQuantity inventoryItem {id}}}} } }"
    query = f"query {search_query} {return_fields}"
    
    if req.product_id:
        variables = { "identifier": { "id": build_product_gid(req.product_id) } }
    elif req.product_handle:
        variables = { "identifier": { "handle": req.product_handle } }
    else:
        raise ValueError("Must provide product_id or product_handle")
    print("Shopify Request Payload:", {"query": query, "variables": variables})
    return {"query": query, "variables": variables}

def build_multiple_products_fetch_request_payload(limit: int = 20, status_filter: str = "status:active,draft") -> Dict[str, Any]:
    """
    Build multiple products fetch payload for Shopify GraphQL API.
    
    Args:
        limit: Number of products to fetch (default: 20)
        status_filter: Status filter for products (default: "status:active,draft")
        
    Returns:
        Dict containing the GraphQL query for fetching multiple products
    """
    
    # Based on your curl example: query GetProducts { products(first: 10) { nodes { id title } } }
    # Adding query parameter for status filtering
    query = f"""
    query GetProducts($query: String!) {{
        products(first: {limit}, query: $query) {{
            nodes {{
                id
                title
                handle
                tags
                status
                variants(first: 10) {{
                    edges {{
                        node {{
                            id
                            title
                            inventoryQuantity
                            inventoryItem {{
                                id
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    """
    
    # Add the status filter as a variable
    variables = {
        "query": status_filter
    }
    
    print("Shopify Multiple Products Request Payload:", {"query": query.strip(), "variables": variables})
    return {"query": query.strip(), "variables": variables}