import requests
import json
from typing import Optional, Dict, Any
import sys
import os
import logging
from .shopify_customer_utils import ShopifyCustomerUtils
from .builders.shopify_gid_builders import build_customer_gid
from .core.shopify_client import initialize_shopify_session
import shopify
from . import shopify_order_utils
from config import config

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Handle imports for both direct execution and module import
try:
    from config import config
except ImportError:
    from backend.config import config

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
        self.graphql_url = config.Shopify.graphql_url
        self.rest_url = config.Shopify.rest_url
        self.token = config.Shopify.token
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.token,
        }

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

    def _make_shopify_request(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a GraphQL request to Shopify"""
        import logging
        import os

        logger = logging.getLogger(__name__)

        # Configure SSL certificates and endpoints based on environment
        environment = os.getenv("ENVIRONMENT", "dev").lower()
        logger.info(f"🌍 Environment: {environment}")

        # SSL Certificate Configuration
        if environment == "production":
            # Production: Ubuntu/Linux environment - use system certificates
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
            logger.info("🔒 Using Ubuntu system SSL certificates for production")
        elif environment in ["dev", "staging"]:
            # Dev/Staging: Use local environment certificate configuration
            local_cert_file = os.getenv("LOCAL_SSL_CERT_FILE")
            if local_cert_file and os.path.exists(local_cert_file):
                # Use certificate specified in .env file
                os.environ["SSL_CERT_FILE"] = local_cert_file
                os.environ["REQUESTS_CA_BUNDLE"] = local_cert_file
                os.environ["CURL_CA_BUNDLE"] = local_cert_file
                logger.info(
                    f"🔒 Using local SSL certificate from env: {local_cert_file}"
                )
            else:
                # Fallback to certifi for local development
                try:
                    import certifi

                    cert_path = certifi.where()
                    if os.path.exists(cert_path):
                        os.environ["SSL_CERT_FILE"] = cert_path
                        os.environ["REQUESTS_CA_BUNDLE"] = cert_path
                        os.environ["CURL_CA_BUNDLE"] = cert_path
                        logger.info(f"🔒 Using certifi SSL certificates: {cert_path}")
                except ImportError:
                    logger.warning(
                        "⚠️ certifi package not found, using system SSL settings"
                    )

        # Endpoint and Token Configuration
        should_use_mock = environment in ["dev", "test"]
        should_use_production_endpoints = environment in ["staging", "production"]

        logger.info(f"🎯 Use mocks: {should_use_mock}")
        logger.info(f"🌐 Use production endpoints: {should_use_production_endpoints}")

        # Return early with mock data if in dev/test environment
        if should_use_mock and not os.getenv("FORCE_REAL_API"):
            logger.info("🎭 Using mock data for dev/test environment")
            return self._get_mock_response(query)

        # DEBUG: Log the request details
        # Extract operation type for better logging
        operation_name = "Unknown"
        query_str = query.get("query", "")
        if "productCreate" in query_str:
            operation_name = "CREATE_PRODUCT"
        elif "productVariantsBulkCreate" in query_str:
            operation_name = "CREATE_VARIANTS_BULK"
        elif "productVariantUpdate" in query_str:
            operation_name = "UPDATE_VARIANT"
        elif "productOptionsCreate" in query_str:
            operation_name = "CREATE_PRODUCT_OPTIONS"
        elif "inventoryAdjustQuantities" in query_str:
            operation_name = "ADJUST_INVENTORY"
        elif "GetInventoryItemId" in query_str:
            operation_name = "GET_INVENTORY_ITEM"
        elif "productUpdate" in query_str:
            operation_name = "UPDATE_PRODUCT"
        elif "product(id:" in query_str and "variants" in query_str:
            operation_name = "GET_PRODUCT_VARIANTS"
        elif "shop" in query_str and "name" in query_str:
            operation_name = "GET_SHOP_INFO"

        # Essential logging - operation only
        logger.info(f"🚀 {operation_name}")

        try:
            response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json=query,
                timeout=30,
                verify=True,  # Use system certificates
            )

            # Shopify always returns 200, so check actual response content for errors
            # Handle different HTTP status codes
            if response.status_code == 401:
                logger.info(f"📥 Response text: {response.text}")
                logger.error("🚨 Shopify authentication error (401): Invalid API token")
                try:
                    error_data = response.json()
                    shopify_error = error_data.get("errors", response.text)
                except (ValueError, KeyError):
                    shopify_error = response.text
                return {
                    "error": "authentication_error",
                    "status_code": 401,
                    "shopify_errors": shopify_error,
                }
            elif response.status_code == 404:
                logger.error("🚨 Shopify store not found (404): Invalid store URL")
                try:
                    error_data = response.json()
                    shopify_error = error_data.get("errors", response.text)
                except (ValueError, KeyError):
                    shopify_error = response.text
                return {
                    "error": "store_not_found",
                    "status_code": 404,
                    "shopify_errors": shopify_error,
                }
            elif response.status_code >= 500:
                logger.error(
                    f"🚨 Shopify server error ({response.status_code}): {response.text}"
                )
                return {
                    "error": "server_error",
                    "status_code": response.status_code,
                    "message": response.text,
                }
            elif response.status_code != 200:
                logger.error(
                    f"🚨 Shopify API error ({response.status_code}): {response.text}"
                )
                return {
                    "error": "api_error",
                    "status_code": response.status_code,
                    "message": response.text,
                }

            # Success - parse JSON response (for status 200)
            result = response.json()

            # Check for GraphQL errors first
            if "errors" in result:
                logger.error(
                    f"❌ {operation_name} failed - GraphQL errors: {result['errors']}"
                )
                return {"error": result["errors"]}

            # Check for user errors in nested operations and determine success/failure
            has_errors = False
            if "data" in result and result["data"]:
                for key, value in result["data"].items():
                    if (
                        isinstance(value, dict)
                        and "userErrors" in value
                        and value["userErrors"]
                    ):
                        has_errors = True
                        logger.error(
                            f"❌ {operation_name} failed - User errors in {key}: {value['userErrors']}"
                        )

            # For CREATE_PRODUCT, also check if we actually got a product back
            if operation_name == "CREATE_PRODUCT" and "data" in result:
                product_create = result["data"].get("productCreate", {})
                product = product_create.get("product", {})
                if not product or not product.get("id"):
                    has_errors = True
                    logger.error(
                        f"❌ {operation_name} failed - No product returned from Shopify"
                    )

            # Log final result
            if has_errors:
                logger.error(f"❌ {operation_name} failed")
            else:
                logger.info(f"✅ {operation_name} successful")

                # Log key success details for specific operations
                if operation_name == "CREATE_PRODUCT" and "data" in result:
                    product = result["data"]["productCreate"].get("product", {})
                    if product.get("id"):
                        logger.info(f"   🆔 Product ID: {product.get('id')}")
                elif operation_name == "CREATE_VARIANTS_BULK" and "data" in result:
                    variants = result["data"]["productVariantsBulkCreate"].get(
                        "productVariants", []
                    )
                    logger.info(f"   🎯 Created {len(variants)} variants")

            return result

        except requests.exceptions.SSLError as ssl_error:
            logger.error(f"🚨 SSL Error - trying without verification: {ssl_error}")
            logger.error(f"🔍 SSL Error type: {type(ssl_error).__name__}")
            logger.error(f"🔍 SSL Error details: {str(ssl_error)}")
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

                # Handle status codes in fallback too
                if response.status_code == 401:
                    logger.error(
                        "🚨 Shopify authentication error (401): Invalid API token"
                    )
                    try:
                        error_data = response.json()
                        shopify_error = error_data.get("errors", response.text)
                    except (ValueError, KeyError):
                        shopify_error = response.text
                    return {
                        "error": "authentication_error",
                        "status_code": 401,
                        "shopify_errors": shopify_error,
                    }
                elif response.status_code == 404:
                    logger.error("🚨 Shopify store not found (404): Invalid store URL")
                    try:
                        error_data = response.json()
                        shopify_error = error_data.get("errors", response.text)
                    except (ValueError, KeyError):
                        shopify_error = response.text
                    return {
                        "error": "store_not_found",
                        "status_code": 404,
                        "shopify_errors": shopify_error,
                    }
                elif response.status_code >= 500:
                    logger.error(
                        f"🚨 Shopify server error ({response.status_code}): {response.text}"
                    )
                    return {
                        "error": "server_error",
                        "status_code": response.status_code,
                        "message": response.text,
                    }
                elif response.status_code != 200:
                    logger.error(
                        f"🚨 Shopify API error ({response.status_code}): {response.text}"
                    )
                    return {
                        "error": "api_error",
                        "status_code": response.status_code,
                        "message": response.text,
                    }

                result = response.json()
                logger.info(f"📋 Fallback response data: {result}")
                return result
            except requests.exceptions.ConnectionError as fallback_conn_error:
                logger.error(f"🚨 Network connection failed: {fallback_conn_error}")
                return None  # True connection error
            except requests.exceptions.Timeout as fallback_timeout_error:
                logger.error(f"🚨 Request timeout: {fallback_timeout_error}")
                return None  # True connection error
            except requests.RequestException as fallback_error:
                logger.error(f"🚨 Fallback request failed: {fallback_error}")
                return None  # True connection error

        except requests.exceptions.ConnectionError as conn_error:
            logger.error(f"🚨 Network connection failed: {conn_error}")
            logger.error(f"🔍 Connection error type: {type(conn_error).__name__}")
            logger.error(f"🔍 Connection error details: {str(conn_error)}")
            return {
                "error": "connection_error",
                "error_type": "network_failure",
                "message": f"Failed to connect to Shopify: {str(conn_error)}",
                "engineering_note": "Check network connectivity, DNS resolution, and Shopify endpoint availability",
            }
        except requests.exceptions.Timeout as timeout_error:
            logger.error(f"🚨 Request timeout: {timeout_error}")
            logger.error(f"🔍 Timeout error type: {type(timeout_error).__name__}")
            logger.error(f"🔍 Timeout error details: {str(timeout_error)}")
            return {
                "error": "timeout_error",
                "error_type": "request_timeout",
                "message": f"Request to Shopify timed out after 30 seconds: {str(timeout_error)}",
                "engineering_note": "Check network latency, Shopify API performance, or increase timeout",
            }
        except requests.RequestException as e:
            logger.error(f"🚨 Request failed: {e}")
            logger.error(f"🔍 Request exception type: {type(e).__name__}")
            logger.error(f"🔍 Request exception details: {str(e)}")
            return {
                "error": "request_exception",
                "error_type": "unknown_request_failure",
                "message": f"Unexpected request error: {str(e)}",
                "engineering_note": "Investigate request configuration, SSL issues, or Shopify API changes",
            }

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
        return shopify_order_utils.cancel_order(order_id, self._make_shopify_request)

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        return shopify_order_utils.get_order_details(order_id, self._make_shopify_request)

    def create_refund(
        self, order_id: str, refund_amount: float, refund_type: str = "refund"
    ) -> Dict[str, Any]:
        return shopify_order_utils.create_refund(
            order_id, refund_amount, refund_type, self._make_shopify_request
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
                location_id = getattr(config, "shopify_location_id", None)
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

    def get_customer_details(
        self,
        customer_email: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch Shopify customer details (id, email, first_name, last_name, tags)

        Uses the Shopify Python library for simpler requests and parsing.
        Provide either customer_email or customer_id. If both provided, customer_id is preferred.
        Prints success/failure messages and returns a structured result.
        """
        try:
            lookup_by = "id" if customer_id else ("email" if customer_email else None)
            if not lookup_by:
                msg = "Provide customer_email or customer_id"
                print(f"❌ {msg}")
                logger.error(msg)
                return {"success": False, "message": msg, "customer": None}

            # Initialize Shopify session
            shop_url = f"{config.Shopify.store_id}.myshopify.com"
            initialize_shopify_session(shop_url, "2025-07", config.Shopify.token)

            # Fetch customer
            if customer_id:
                cust = shopify.Customer.find(customer_id)
                # Some versions return None when not found
                if not cust or not getattr(cust, "id", None):
                    msg = f"Customer not found for id: {customer_id}"
                    print(f"📭 {msg}")
                    logger.info(msg)
                    return {"success": True, "message": "No customer found", "customer": None}
            else:
                results = shopify.Customer.search(query=f"email:{customer_email}")
                if not results:
                    msg = f"Customer not found for email: {customer_email}"
                    print(f"📭 {msg}")
                    logger.info(msg)
                    return {"success": True, "message": "No customer found", "customer": None}
                cust = results[0]

            # Normalize tags to list[str]
            tags_raw = getattr(cust, "tags", [])
            if isinstance(tags_raw, str):
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            elif isinstance(tags_raw, list):
                tags = [str(t).strip() for t in tags_raw if str(t).strip()]
            else:
                tags = []

            customer = {
                "id": getattr(cust, "id", None),
                "email": getattr(cust, "email", None),
                "first_name": getattr(cust, "first_name", None),
                "last_name": getattr(cust, "last_name", None),
                "tags": tags,
            }

            print(
                f"✅ Customer found: {customer.get('first_name','')} {customer.get('last_name','')} "
                f"({customer.get('email','')}) | ID: {customer.get('id')}"
            )
            logger.info(
                f"✅ Customer found: {customer.get('first_name','')} {customer.get('last_name','')} "
                f"({customer.get('email','')})"
            )
            return {"success": True, "message": "Customer found", "customer": customer}

        except Exception as e:
            # Try to classify credential problems
            err_text = str(e)
            if "401" in err_text or "Unauthorized" in err_text:
                msg = "Shopify authentication error (credentials likely wrong)"
            else:
                msg = f"Error fetching customer details: {err_text}"
            print(f"❌ {msg}")
            logger.error(msg)
            return {"success": False, "message": msg, "customer": None}

    def _make_shopify_rest_request(
        self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a REST API request to Shopify"""
        from config import config

        # For development/testing mode when Shopify credentials aren't available
        should_use_mock = (
            not self.token
            or config.environment.lower() in ["dev", "test"]
        )

        if should_use_mock and not os.getenv("FORCE_REAL_API"):
            logger.info("🎭 Using mock data for REST API dev/test environment")
            # Return a mock successful response for variant update
            if "variants" in endpoint and method == "PUT":
                # Extract variant ID from endpoint for more realistic mock
                variant_id = (
                    endpoint.split("/")[1].split(".")[0] if "/" in endpoint else "12345"
                )
                return {
                    "variant": {
                        "id": int(variant_id) if variant_id.isdigit() else 12345,
                        "taxable": data.get("variant", {}).get("taxable", False)
                        if data
                        else False,
                        "requires_shipping": data.get("variant", {}).get(
                            "requires_shipping", False
                        )
                        if data
                        else False,
                        "inventory_management": data.get("variant", {}).get(
                            "inventory_management", "shopify"
                        )
                        if data
                        else "shopify",
                    }
                }
            return {"success": True, "message": "Mock REST response"}

        # Build full URL
        full_url = f"{self.rest_url}/{endpoint.lstrip('/')}"

        logger.info(f"🚀 REST {method} {endpoint}")

        try:
            # Use explicit SSL certificate bundle for production
            cert_bundle = (
                "/etc/ssl/certs/ca-certificates.crt"
                if os.getenv("ENVIRONMENT") == "production"
                else True
            )

            if method.upper() == "GET":
                response = requests.get(
                    full_url,
                    headers=self.headers,
                    timeout=30,
                    verify=cert_bundle,
                )
            elif method.upper() == "PUT":
                response = requests.put(
                    full_url,
                    headers=self.headers,
                    json=data,
                    timeout=30,
                    verify=cert_bundle,
                )
            elif method.upper() == "POST":
                response = requests.post(
                    full_url,
                    headers=self.headers,
                    json=data,
                    timeout=30,
                    verify=cert_bundle,
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Handle different HTTP status codes
            if response.status_code == 401:
                logger.error(f"❌ REST {method} failed - authentication error (401)")
                logger.error(f"📤 Error response: {response.text}")
                return {
                    "error": "authentication_error",
                    "status_code": 401,
                    "message": response.text,
                }
            elif response.status_code == 404:
                logger.error("🚨 Resource not found (404)")
                return {
                    "error": "not_found",
                    "status_code": 404,
                    "message": response.text,
                }
            elif response.status_code >= 500:
                logger.error(
                    f"🚨 Shopify server error ({response.status_code}): {response.text}"
                )
                return {
                    "error": "server_error",
                    "status_code": response.status_code,
                    "message": response.text,
                }
            elif response.status_code not in [200, 201]:
                logger.error(
                    f"🚨 Shopify REST API error ({response.status_code}): {response.text}"
                )
                return {
                    "error": "api_error",
                    "status_code": response.status_code,
                    "message": response.text,
                }

            # Success - parse JSON response
            result = response.json()

            # Check if the response indicates success or has errors
            if "errors" in result:
                logger.error(
                    f"❌ REST {method} failed - Response errors: {result['errors']}"
                )
                return {"error": "shopify_errors", "message": result["errors"]}

            logger.info(f"✅ REST {method} successful")
            return result

        except requests.exceptions.SSLError as ssl_error:
            logger.error(f"🚨 SSL Error - trying without verification: {ssl_error}")
            # Fallback: try without SSL verification (for development)
            try:
                logger.warning(
                    "⚠️ Retrying Shopify REST request without SSL verification"
                )
                if method.upper() == "GET":
                    response = requests.get(
                        full_url, headers=self.headers, timeout=30, verify=False
                    )
                elif method.upper() == "PUT":
                    response = requests.put(
                        full_url,
                        headers=self.headers,
                        json=data,
                        timeout=30,
                        verify=False,
                    )
                elif method.upper() == "POST":
                    response = requests.post(
                        full_url,
                        headers=self.headers,
                        json=data,
                        timeout=30,
                        verify=False,
                    )

                if response.status_code in [200, 201]:
                    result = response.json()
                    logger.info(
                        "✅ Shopify REST request successful (no SSL verification)"
                    )
                    return result
                else:
                    logger.error(
                        f"❌ Shopify REST request failed: {response.status_code} - {response.text}"
                    )
                    return {
                        "error": "request_failed",
                        "status_code": response.status_code,
                        "message": response.text,
                    }
            except Exception as retry_error:
                logger.error(f"❌ Retry failed: {retry_error}")
                return {"error": "ssl_and_retry_failed", "message": str(retry_error)}

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request exception: {e}")
            return {"error": "request_exception", "message": str(e)}
        except Exception as e:
            logger.error(f"❌ Unexpected error in REST request: {e}")
            return {"error": "unexpected_error", "message": str(e)}

    def update_variant_rest(
        self, variant_id: str, variant_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a product variant using Shopify REST API"""
        # Extract numeric ID from GID if needed
        if variant_id.startswith("gid://shopify/ProductVariant/"):
            numeric_id = variant_id.split("/")[-1]
        else:
            numeric_id = variant_id

        endpoint = f"variants/{numeric_id}.json"

        # Wrap in the format Shopify REST API expects
        payload = {"variant": variant_data}

        response = self._make_shopify_rest_request(endpoint, "PUT", payload)

        if response and "variant" in response:
            return {
                "success": True,
                "message": "Variant updated successfully",
                "variant": response["variant"],
            }
        elif response and "error" in response:
            logger.error(
                f"❌ Variant update failed: {response.get('message', 'Unknown error')}"
            )
            return {
                "success": False,
                "error": response["error"],
                "message": response.get("message", "Variant update failed"),
            }
        else:
            logger.error("❌ Unexpected response format from variant update")
            return {
                "success": False,
                "error": "unexpected_response",
                "message": "Unexpected response format",
            }

    def set_product_as_waitlist_only(self, product_id: str) -> Dict[str, Any]:
        """
        Set a product's tags to include "waitlist-only" via GraphQL productUpdate.

        Args:
            product_id: Shopify product ID (numeric or full GID)

        Returns:
            Dict with success flag and returned product/tags or error details.
        """
        try:
            # Normalize to Shopify GID if a numeric ID is provided
            if isinstance(product_id, str) and product_id.startswith("gid://shopify/Product/"):
                product_gid = product_id
            else:
                product_gid = f"gid://shopify/Product/{product_id}"

            mutation = (
                "mutation {\n"
                "  productUpdate(input: {id: \"" + product_gid + "\", tags: [\"waitlist-only\"]}) {\n"
                "    product { id tags }\n"
                "    userErrors { field message }\n"
                "  }\n"
                "}"
            )

            payload = {"query": mutation}
            result = self._make_shopify_request(payload)

            if not result:
                logger.error("❌ productUpdate failed - raw response: None")
                return {"success": False, "error": "no_response", "message": "No response from Shopify"}

            if "errors" in result:
                try:
                    logger.error(f"❌ productUpdate failed - GraphQL errors. Raw response: {json.dumps(result, indent=2)}")
                except Exception:
                    logger.error("❌ productUpdate failed - GraphQL errors. Raw response present but could not be serialized")
                return {"success": False, "error": "graphql_errors", "details": result["errors"]}

            update = result.get("data", {}).get("productUpdate", {})
            user_errors = update.get("userErrors", [])
            if user_errors:
                try:
                    logger.error(f"❌ productUpdate failed - userErrors present. Raw response: {json.dumps(result, indent=2)}")
                except Exception:
                    logger.error("❌ productUpdate failed - userErrors present. Raw response present but could not be serialized")
                return {
                    "success": False,
                    "error": "user_errors",
                    "details": user_errors,
                }

            product = update.get("product")
            if not product:
                try:
                    logger.error(f"❌ productUpdate failed - no product returned. Raw response: {json.dumps(result, indent=2)}")
                except Exception:
                    logger.error("❌ productUpdate failed - no product returned. Raw response present but could not be serialized")
                return {
                    "success": False,
                    "error": "no_product_returned",
                    "message": "productUpdate returned no product",
                }

            return {"success": True, "product": product}

        except Exception as e:
            logger.error(f"Error setting product {product_id} as waitlist-only: {e}")
            return {"success": False, "error": str(e)}
