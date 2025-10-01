import logging
from config import config
from typing import Optional, Dict, Any
from ..models.requests import FetchOrderRequest
from ..models.graphql_queries import ShopifyGraphQLQuery

def build_product_gid(product_id: str) -> str:
    return f"gid://shopify/Product/{product_id}"

logger = logging.getLogger(__name__)

###############################################################################
# Inventory
###############################################################################

def build_get_inventory_item_and_quantity(variant_gid: str) -> Dict[str, Any]:
    query = (
        "query GetInventoryItemId($variantId: ID!) {\n"
        "  productVariant(id: $variantId) {\n"
        "    id\n"
        "    inventoryItem { id }\n"
        "    inventoryQuantity\n"
        "  }\n"
        "}"
    )
    return {"query": query, "variables": {"variantId": variant_gid}}


def build_adjust_inventory_mutation(
    *,
    inventory_item_id: str,
    delta: int,
    location_id: str,
    reference_uri: Optional[str] = None,
    reason: str = "correction",
    name: str = "available",
) -> Dict[str, Any]:
    query = (
        "mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {\n"
        "  inventoryAdjustQuantities(input: $input) {\n"
        "    userErrors { field message }\n"
        "    inventoryAdjustmentGroup { createdAt reason referenceDocumentUri changes { name delta } }\n"
        "  }\n"
        "}"
    )
    variables = {
        "input": {
            "reason": reason,
            "name": name,
            "referenceDocumentUri": reference_uri,
            "changes": [
                {
                    "delta": delta,
                    "inventoryItemId": inventory_item_id,
                    "locationId": location_id,
                }
            ],
        }
    }
    return {"query": query, "variables": variables}

# --- Orders ---

def build_shopify_order_fetch_query(req: FetchOrderRequest) -> Dict[str, Any]:
    """
    Build a single Shopify order search query using the structured model.
    Returns a payload with "query" and "variables".
    """
    if req.order_id:
        search = f"id:{req.order_id}"
    elif req.order_number:
        search = f"name:#{req.order_number}"
    elif req.email:
        search = f"email:{req.email}"
    else:
        raise ValueError("Must provide order_id, order_number, or email")

    return ShopifyGraphQLQuery.order_search(search).to_payload()


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

