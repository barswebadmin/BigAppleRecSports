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

# GraphQL Queries for inventory management
GET_INVENTORY_ITEM_AND_QUANTITY = """
query GetInventoryItemId($variantId: ID!) {
  productVariant(id: $variantId) {
    id
    inventoryItem {
      id
    }
    inventoryQuantity
  }
}
"""

ADJUST_INVENTORY = """
mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
  inventoryAdjustQuantities(input: $input) {
    userErrors {
      field
      message
    }
    inventoryAdjustmentGroup {
      createdAt
      reason
      referenceDocumentUri
      changes {
        name
        delta
      }
    }
  }
}
"""


class ShopifyService:
    def __init__(self):
        self.shopify_customer_utils = ShopifyCustomerUtils(self._make_shopify_request)
        self.shopify_order_utils = ShopifyOrderUtils(self._make_shopify_request)
        self.graphql_url = settings.graphql_url
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": settings.shopify_token,
        }

    def _make_shopify_request(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a GraphQL request to Shopify"""
        import logging
        import os

        logger = logging.getLogger(__name__)

        # FIX: Ensure SSL certificates are properly configured for Render (Ubuntu)
        # Only set Ubuntu SSL paths if we're in a production/cloud environment
        if os.getenv("ENVIRONMENT") == "production" and not os.path.exists(
            "/opt/homebrew"
        ):
            if not os.getenv("SSL_CERT_FILE") or not os.path.exists(
                os.getenv("SSL_CERT_FILE", "")
            ):
                os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"
            if not os.getenv("REQUESTS_CA_BUNDLE") or not os.path.exists(
                os.getenv("REQUESTS_CA_BUNDLE", "")
            ):
                os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
            if not os.getenv("CURL_CA_BUNDLE") or not os.path.exists(
                os.getenv("CURL_CA_BUNDLE", "")
            ):
                os.environ["CURL_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"


        logger = logging.getLogger(__name__)

        # DEBUG: Log the request details
        logger.info(f"🔗 Making Shopify request to: {self.graphql_url}")
        logger.info(f"🔑 Headers: {self.headers}")
        logger.info(f"📤 Query: {query}")
        logger.info(f"🔒 SSL_CERT_FILE: {os.getenv('SSL_CERT_FILE')}")
        logger.info(f"🔒 REQUESTS_CA_BUNDLE: {os.getenv('REQUESTS_CA_BUNDLE')}")

        try:
            response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json=query,
                timeout=30,
                verify=True,  # Explicitly enable SSL verification
            )
            logger.info(f"📥 Response status: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.info(f"📋 Response data: {result}")
            return result
        except requests.exceptions.SSLError as ssl_error:
            logger.error(f"🚨 SSL Error - trying without verification: {ssl_error}")
            # Fallback: try without SSL verification (for development)
            try:
                logger.warning("⚠️ Retrying Shopify request without SSL verification")
                response = requests.post(
                    self.graphql_url,
                    headers=self.headers,
                    json=query,
                    timeout=30,
                    verify=False,
                )
                logger.info(f"📥 Fallback response status: {response.status_code}")
                response.raise_for_status()
                result = response.json()
                logger.info(f"📋 Fallback response data: {result}")
                return result
            except requests.RequestException as fallback_error:
                logger.error(f"🚨 Fallback request also failed: {fallback_error}")
                return None
        except requests.RequestException as e:
            logger.error(f"🚨 Request failed: {e}")
            return None

    # Forwarding from ShopifyCustomerUtils
    def get_customer_with_tags(self, email: str) -> Optional[Dict[str, Any]]:
        return self.shopify_customer_utils.get_customer_with_tags(email)

    def get_customers_batch(self, emails: list) -> Dict[str, Optional[Dict[str, Any]]]:
        return self.shopify_customer_utils.get_customers_batch(emails)

    def add_tag_to_customer(
        self, customer_id: str, tag: str, existing_tags: Optional[list] = None
    ) -> bool:
        return self.shopify_customer_utils.add_tag_to_customer(
            customer_id, tag, existing_tags
        )

    def create_segment(self, name: str, query: str) -> Optional[str]:
        return self.shopify_customer_utils.create_segment(name, query)

    def create_discount_code(
        self,
        code: str,
        usage_limit: int,
        season: str,
        year: int,
        segment_id: str,
        discount_amount: float,
    ) -> bool:
        return self.shopify_customer_utils.create_discount_code(
            code, usage_limit, season, year, segment_id, discount_amount
        )

    # Forwarding from ShopifyOrderUtils
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return self.shopify_order_utils.cancel_order(order_id)

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        return self.shopify_order_utils.get_order_details(order_id)

    def create_refund(
        self, order_id: str, refund_amount: float, refund_type: str = "refund"
    ) -> Dict[str, Any]:
        return self.shopify_order_utils.create_refund(
            order_id, refund_amount, refund_type
        )

    # Inventory management methods
    def get_inventory_item_and_quantity(self, variant_gid: str) -> Dict[str, Any]:
        """Get inventory item ID and available quantity for a given variant GID"""
        try:
            query = {
                "query": GET_INVENTORY_ITEM_AND_QUANTITY,
                "variables": {"variantId": variant_gid},
            }

            data = self._make_shopify_request(query)

            if (
                not data
                or not data.get("data")
                or not data["data"].get("productVariant")
            ):
                raise ValueError(
                    f"Could not get inventory info for variant {variant_gid}"
                )

            variant = data["data"]["productVariant"]
            return {
                "success": True,
                "inventoryItemId": variant["inventoryItem"]["id"],
                "inventoryQuantity": variant["inventoryQuantity"],
            }

        except Exception as e:
            logger.error(
                f"Error getting inventory item and quantity for {variant_gid}: {str(e)}"
            )
            return {
                "success": False,
                "message": str(e),
                "inventoryItemId": None,
                "inventoryQuantity": None,
            }

    def adjust_inventory(
        self, inventory_item_id: str, delta: int, location_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Adjust inventory using inventoryAdjustQuantities mutation"""
        try:
            # Use default location if not provided
            if not location_id:
                location_id = getattr(settings, "shopify_location_id", None)
                if not location_id:
                    raise ValueError(
                        "SHOPIFY_LOCATION_ID is required for inventory adjustments"
                    )

                # Ensure location_id is in proper global ID format
                if not location_id.startswith("gid://shopify/Location/"):
                    location_id = f"gid://shopify/Location/{location_id}"

            from datetime import datetime

            reference_uri = (
                f"logistics://slackrefundworkflow/{datetime.utcnow().isoformat()}"
            )

            variables = {
                "input": {
                    "reason": "correction",
                    "name": "available",
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

            query = {"query": ADJUST_INVENTORY, "variables": variables}

            data = self._make_shopify_request(query)

            # Enhanced debugging for Shopify response
            logger.info(
                f"🔍 Shopify inventory adjustment response: {json.dumps(data, indent=2) if data else 'None'}"
            )

            if not data:
                raise ValueError("No response received from Shopify")

            if "errors" in data:
                error_msg = json.dumps(data["errors"], indent=2)
                raise ValueError(f"Shopify GraphQL errors: {error_msg}")

            if not data.get("data"):
                raise ValueError(
                    f"Invalid response structure from Shopify: {json.dumps(data, indent=2)}"
                )

            user_errors = (
                data["data"].get("inventoryAdjustQuantities", {}).get("userErrors", [])
            )
            if user_errors:
                error_messages = [f"{e['field']}: {e['message']}" for e in user_errors]
                raise ValueError(
                    "Inventory adjustment failed: " + "; ".join(error_messages)
                )

            return {
                "success": True,
                "message": f"Successfully adjusted inventory by {delta}",
                "data": data["data"]["inventoryAdjustQuantities"],
            }

        except Exception as e:
            logger.error(f"Error adjusting inventory for {inventory_item_id}: {str(e)}")
            return {"success": False, "message": str(e)}

    def get_customer_by_email(self, email: str) -> Dict[str, Any]:
        """
        Fetch customer data by email address

        Args:
            email: Customer email address

        Returns:
            Dict containing customer data or error information
        """
        try:
            logger.info(f"🔍 Fetching customer data for email: {email}")

            query = f"""
            query {{
                customers(first: 1, query: "email:{email}") {{
                    edges {{
                        node {{
                            id
                            firstName
                            lastName
                            email
                            displayName
                        }}
                    }}
                }}
            }}
            """

            data = self._make_shopify_request({"query": query})

            if not data:
                logger.error("❌ No response from Shopify API")
                return {
                    "success": False,
                    "message": "No response from Shopify API",
                    "customer": None,
                }

            if "errors" in data:
                error_msg = json.dumps(data["errors"], indent=2)
                logger.error(f"❌ Shopify GraphQL errors: {error_msg}")
                return {
                    "success": False,
                    "message": f"GraphQL errors: {error_msg}",
                    "customer": None,
                }

            customers = data.get("data", {}).get("customers", {}).get("edges", [])

            if not customers:
                logger.info(f"📭 No customer found with email: {email}")
                return {
                    "success": True,
                    "message": "No customer found",
                    "customer": None,
                }

            customer = customers[0]["node"]
            logger.info(
                f"✅ Found customer: {customer.get('firstName', '')} {customer.get('lastName', '')} ({customer.get('email', '')})"
            )

            return {"success": True, "message": "Customer found", "customer": customer}

        except Exception as e:
            logger.error(f"❌ Error fetching customer by email {email}: {str(e)}")
            return {"success": False, "message": str(e), "customer": None}
