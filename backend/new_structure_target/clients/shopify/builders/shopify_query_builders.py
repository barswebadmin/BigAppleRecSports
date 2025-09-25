import logging
from config import config
from typing import Optional, Dict, Any
from .shopify_gid_builders import build_product_gid

logger = logging.getLogger(__name__)


# --- Orders ---
def get_order_details_query(order_id: Optional[str] = None, order_number: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a GraphQL payload to fetch order details.

    - If order_id is provided (Shopify GID), use order(id: $id)
    - If order_number is provided (e.g., "#12345" or "12345"), use orders(first:1, query: $query)
      with query string matching the order name.
    """
    if not order_id and not order_number:
        raise ValueError("Either order_id or order_number must be provided")

    if order_id:
        return {
            "query": (
                "query getOrderDetails($id: ID!) {\n"
                "  order(id: $id) {\n"
                "    id\n"
                "    name\n"
                "    email\n"
                "    customer { id email }\n"
                "    transactions { id kind gateway parentTransaction { id } }\n"
                "  }\n"
                "}"
            ),
            "variables": {"id": order_id},
        }

    # Normalize order_number – ensure it includes leading '#'
    on = order_number or ""
    if not on.startswith("#"):
        on = f"#{on}"
    # Shopify Admin search syntax can match name via name:<value>
    query_string = f"name:{on}"

    return {
        "query": (
            "query getOrderByName($q: String!) {\n"
            "  orders(first: 1, query: $q) {\n"
            "    edges {\n"
            "      node {\n"
            "        id\n"
            "        name\n"
            "        email\n"
            "        customer { id email }\n"
            "        transactions { id kind gateway parentTransaction { id } }\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "}"
        ),
        "variables": {"q": query_string},
    }


def get_product_details_query(product_id: Optional[str], product_handle: Optional[str]) -> Dict[str, Any]:
    """Create a get product details query"""
    query = ""
    variables = {}
    if not product_id and not product_handle:
        raise ValueError("Either product_id or product_handle must be provided")
    elif product_id:
        query = "query($identifier: ProductIdentifierInput!) { product: productByIdentifier(identifier: $identifier) { id handle title tags } }"
        variables = { "identifier": { "id": build_product_gid(product_id) } }
    elif product_handle:
        query = "query ($handle: String!) { productByHandle(handle: $handle) { id title productType description vendor } }"
        variables = { "handle": product_handle }
    return {
        "query": query,
        "variables": variables
    }





# def update_product_handle_query(product_id: str, handle: str) -> Dict[str, Any]:

#     """Create a update product handle query"""
#     return {
#         "query": """
#             mutation updateProductHandle($productId: ID!, $handle: String!) {
#                 updateProductHandle(productId: $productId, handle: $handle) {
#                     product {
#                         id
#                         // update product handle
# curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-01/graphql.json" \
#   -H "Content-Type: application/json" \
#   -H "X-Shopify-Access-Token: shopify_token" \
#   -d '{
#     "query": "mutation productUpdate($input: ProductInput!) { productUpdate(input: $input) { product { id handle } userErrors { field message } } }",
#     "variables": {
#       "input": {
#         "id": "gid://shopify/Product/7461773082718",
#         "handle": "2025-fall-pickleball-thursday-opendiv"
#       }
#     }
#   }'




# def update_product_with_new_media_query(product_id: str, media_id: str) -> Dict[str, Any]:
#     """Create a update product with new media query"""
#     return {
#         "query": """
#             mutation updateProductWithNewMedia($productId: ID!, $mediaId: ID!) {
#                 updateProductWithNewMedia(productId: $productId, mediaId: $mediaId) {
#                     product {
#                         id
#                         curl -X POST \
# https://09fe59-3.myshopify.com/admin/api/2025-10/graphql.json \
# -H 'Content-Type: application/json' \
# -H 'X-Shopify-Access-Token: shopify_token' \
# -d '{
# "query": "mutation UpdateProductWithNewMedia($product: ProductUpdateInput!, $media: [CreateMediaInput!]) { productUpdate(product: $product, media: $media) { product { id media(first: 10) { nodes { alt mediaContentType preview { status } } } } userErrors { field message } } }",
#  "variables": {
#     "product": {
#       "id": "gid://shopify/Product/{product_gid}"
#     },
#     "media": [
#       {
#         "originalSource": {sold_out_image_url},
#         "alt": "Sold out image for {sport}",
#         "mediaContentType": "IMAGE"
#       }
#     ]
#   }
# }'







# def create_refund_query(order_id: str, refund_amount: float, refund_type: str) -> Dict[str, Any]:
#     """Create a refund query"""
#     return {
#         "query": """
#             mutation refundCreate($orderId: ID!, $amount: Money!, $type: RefundType!) {
#                 refundCreate(orderId: $orderId, amount: $amount, type: $type) {
#                     refund {
#                         id
#                     }
#                 }
#             }
#         """
#     }








# orders query

# curl -X POST "https://09fe59-3.myshopify.com/admin/api/2025-07/graphql.json" \
#   -H "Content-Type: application/json" \
#   -H "X-Shopify-Access-Token: token" \
#   -w '{"status_code": %{http_code}}\n' \
#   -d '{
#     "query": "query { orders(first: 1, query: \"id:5236092698718\") { edges { node { id name email totalPriceSet { shopMoney { amount currencyCode } } } } } }"
#   }'

# data.orders.edges is empty
# search[0].warnings for 400/422 (gid instead of id)
# warnings has one object with `field` and `message`

# order_number:
# "field": "order_number",
#             "message": "Invalid search field for this query."

# data.orders.edges is empty but no `search` for order id not found

