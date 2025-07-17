import requests
import json
from typing import Optional, Dict, Any
import sys
import os
import logging
from .shopify_customer_utils import ShopifyCustomerUtils
from .shopify_order_utils import ShopifyOrderUtils

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Handle imports for both direct execution and module import
try:
    from config import settings
except ImportError:
    from backend.config import settings

logger = logging.getLogger(__name__)

class ShopifyService:
    def __init__(self):
        self.shopify_customer_utils = ShopifyCustomerUtils(self._make_shopify_request)
        self.shopify_order_utils = ShopifyOrderUtils(self._make_shopify_request)
        self.graphql_url = settings.graphql_url
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": settings.shopify_token
        }

    def _make_shopify_request(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a GraphQL request to Shopify"""
        try:
            response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json=query,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return None


    # Forwarding from ShopifyCustomerUtils
    def get_customer_with_tags(self, email: str) -> Optional[Dict[str, Any]]:
        return self.shopify_customer_utils.get_customer_with_tags(email)

    def get_customer_id(self, email: str) -> Optional[str]:
        return self.shopify_customer_utils.get_customer_id(email)

    def get_customers_batch(self, emails: list) -> Dict[str, Optional[Dict[str, Any]]]:
        return self.shopify_customer_utils.get_customers_batch(emails)

    def add_tag_to_customer(self, customer_id: str, tag: str, existing_tags: Optional[list] = None) -> bool:
        return self.shopify_customer_utils.add_tag_to_customer(customer_id, tag, existing_tags)

    def create_segment(self, name: str, query: str) -> Optional[str]:
        return self.shopify_customer_utils.create_segment(name, query)

    def create_discount_code(self, code: str, usage_limit: int, season: str, year: int, segment_id: str, discount_amount: float) -> bool:
        return self.shopify_customer_utils.create_discount_code(code, usage_limit, season, year, segment_id, discount_amount)

    # Forwarding from ShopifyOrderUtils
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return self.shopify_order_utils.cancel_order(order_id)

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        return self.shopify_order_utils.get_order_details(order_id)

    def create_refund(self, order_id: str, refund_amount: float, refund_type: str = "refund") -> Dict[str, Any]:
        return self.shopify_order_utils.create_refund(order_id, refund_amount, refund_type)