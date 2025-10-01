from typing import Dict, Any
from ..models import FetchProductRequest
from ...integrations.shopify.client.shopify_client import ShopifyClient, ShopifyResponse
import sys

def fetch_product_from_shopify(request_details: FetchProductRequest) -> ShopifyResponse:
    """
    Fetch product details from Shopify
    """
    shopify_client = ShopifyClient()
    return shopify_client.fetch_product_details(request_details)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        key = sys.argv[1]
        result = fetch_product_from_shopify(FetchProductRequest(product_id=key))
        print(result)
    else:
        print("Usage: python3 fetch_product_from_shopify.py <product_id>")