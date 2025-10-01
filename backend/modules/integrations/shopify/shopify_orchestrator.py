import requests
import json
from typing import Optional, Dict, Any
import sys
import os
import logging

from config import config
from modules.integrations.shopify.models import ShopifyResponse
from modules.products.models import FetchProductRequest
from .client.shopify_client import ShopifyClient
from .builders.request_builders import build_order_fetch_request_payload, build_product_fetch_request_payload
from modules.orders.models import FetchOrderRequest

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


class ShopifyOrchestrator:
    def __init__(self):
        self._client: ShopifyClient = ShopifyClient(config.Shopify)
    
    def fetch_order_details(
        self,
        *,
        request_args: FetchOrderRequest
    ) -> ShopifyResponse:
        """
        Fetch order details with a single request: prefer order_id if provided,
        otherwise use order_number. Callers must validate inputs.
        """
       
        payload = build_order_fetch_request_payload(request_args)

        resp = self._client.send_request(payload)
        return resp


    def _get_mock_response(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock response for dev/test environments"""
        # Extract query type from the GraphQL query
        query_str = query.get("query", "")

        if "productCreate" in query_str:
            return {
                "data": {
                    "productCreate": {
                        "product": {
                            "id": "gid://shopify/Product/8123456789012345678",
                            "title": "Mock Product",
                            "handle": "mock-product",
                        },
                        "userErrors": [],
                    }
                }
            }
        elif "productOptionsCreate" in query_str:
            return {
                "data": {
                    "productOptionsCreate": {
                        "product": {"id": "gid://shopify/Product/8123456789012345678"},
                        "userErrors": [],
                    }
                }
            }
        elif "productVariantUpdate" in query_str:
            return {
                "data": {
                    "productVariantUpdate": {
                        "productVariant": {
                            "id": "gid://shopify/ProductVariant/45123456789012345678"
                        },
                        "userErrors": [],
                    }
                }
            }
        elif "productVariantsBulkCreate" in query_str:
            return {
                "data": {
                    "productVariantsBulkCreate": {
                        "productVariants": [
                            {"id": "gid://shopify/ProductVariant/45123456789012345679"},
                            {"id": "gid://shopify/ProductVariant/45123456789012345680"},
                            {"id": "gid://shopify/ProductVariant/45123456789012345681"},
                        ],
                        "userErrors": [],
                    }
                }
            }
        else:
            # Generic mock response
            return {
                "data": {
                    "mock": True,
                    "message": "Mock response for dev/test environment",
                }
            }

    @property
    def shopify_client(self) -> ShopifyClient:
        return self._client


    