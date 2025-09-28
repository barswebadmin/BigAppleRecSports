import requests
import json
from typing import Optional, Dict, Any
import sys
import os
import logging

from backend.models.shopify.requests import FetchOrderRequest
from .core.shopify_client import ShopifyClient
from .builders.shopify_query_builders import build_adjust_inventory_mutation, build_get_inventory_item_and_quantity
from config import config

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Handle imports for both direct execution and module import
try:
    from config import config
except ImportError:
    from backend.config import config

logger = logging.getLogger(__name__)


class ShopifyService:
    def __init__(self):
        self._client: ShopifyClient = ShopifyClient()


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


    

    def fetch_order(self, request_args: FetchOrderRequest) -> Dict[str, Any]:
        """Fetch a single order via ShopifyClient using either order id, order number, or email"""

        try:
            client = self.shopify_client
            resp = client.fetch_order_details(request_args=request_args)
            out = resp.to_dict()
            # order_node = out.get("order")
            # if isinstance(order_node, dict):
            #     order_obj = map_order_node_to_order(order_node)
            #     out["order"] = order_obj.model_dump() if order_obj else None
            return out
        except Exception as e:
            return {"success": False, "message": str(e)}
    