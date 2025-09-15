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
        self.rest_url = settings.rest_url
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": settings.shopify_token,
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

        logger.info(f"🚀 SHOPIFY API REQUEST - {operation_name}")
        logger.info(f"🔗 Endpoint: {self.graphql_url}")
        logger.info(f"🔑 Headers: {self.headers}")
        logger.info(f"📤 Request Query: {json.dumps(query, indent=2)}")
        logger.info(
            f"🔒 SSL Configuration - CERT_FILE: {os.getenv('SSL_CERT_FILE')}, CA_BUNDLE: {os.getenv('REQUESTS_CA_BUNDLE')}"
        )

        try:
            # Use explicit SSL certificate bundle for production
            cert_bundle = (
                "/etc/ssl/certs/ca-certificates.crt"
                if os.getenv("ENVIRONMENT") == "production"
                else True
            )

            response = requests.post(
                self.graphql_url,
                headers=self.headers,
                json=query,
                timeout=30,
                verify=cert_bundle,  # Use explicit certificate bundle
            )

            # Enhanced response logging
            logger.info(f"📥 SHOPIFY API RESPONSE - {operation_name}")
            logger.info(f"📊 Status Code: {response.status_code}")
            logger.info(f"📈 Response Headers: {dict(response.headers)}")

            # Log response size and timing info if available
            content_length = response.headers.get("content-length", "unknown")
            logger.info(f"📏 Response Size: {content_length} bytes")

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

            # Success - parse JSON response
            result = response.json()

            # Enhanced success logging
            logger.info(f"✅ SHOPIFY API SUCCESS - {operation_name}")
            logger.info("📋 Response Summary:")

            # Log key response details based on operation type
            if "data" in result:
                data = result["data"]
                if operation_name == "CREATE_PRODUCT" and "productCreate" in data:
                    product = data["productCreate"].get("product", {})
                    logger.info(f"   🆔 Product ID: {product.get('id')}")
                    logger.info(f"   📝 Product Title: {product.get('title')}")
                    logger.info(f"   🔗 Product Handle: {product.get('handle')}")
                elif (
                    operation_name == "CREATE_VARIANTS_BULK"
                    and "productVariantsBulkCreate" in data
                ):
                    variants = data["productVariantsBulkCreate"].get(
                        "productVariants", []
                    )
                    logger.info(f"   🎯 Created Variants: {len(variants)}")
                    for i, variant in enumerate(variants):
                        logger.info(
                            f"     Variant {i+1}: {variant.get('id')} - {variant.get('title', 'No title')}"
                        )
                elif (
                    operation_name == "UPDATE_VARIANT"
                    and "productVariantUpdate" in data
                ):
                    variant = data["productVariantUpdate"].get("productVariant", {})
                    logger.info(f"   🎯 Updated Variant: {variant.get('id')}")
                elif (
                    operation_name == "ADJUST_INVENTORY"
                    and "inventoryAdjustQuantities" in data
                ):
                    changes = (
                        data["inventoryAdjustQuantities"]
                        .get("inventoryAdjustmentGroup", {})
                        .get("changes", [])
                    )
                    logger.info(f"   📦 Inventory Changes: {len(changes)}")
                    for change in changes:
                        logger.info(
                            f"     {change.get('name')}: {change.get('delta', 0):+d}"
                        )

            # Log any errors in the response
            if "errors" in result:
                logger.warning(f"⚠️ GraphQL Errors in Response: {result['errors']}")

            # Check for userErrors in the data
            if "data" in result:
                for key, value in result["data"].items():
                    if (
                        isinstance(value, dict)
                        and "userErrors" in value
                        and value["userErrors"]
                    ):
                        logger.warning(f"⚠️ User Errors in {key}: {value['userErrors']}")

            logger.info(f"📤 Full Response: {json.dumps(result, indent=2)}")
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
            return None  # True connection error
        except requests.exceptions.Timeout as timeout_error:
            logger.error(f"🚨 Request timeout: {timeout_error}")
            return None  # True connection error
        except requests.RequestException as e:
            logger.error(f"🚨 Request failed: {e}")
            return None  # True connection error

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

    def _make_shopify_rest_request(
        self, endpoint: str, method: str = "GET", data: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a REST API request to Shopify"""
        from config import settings

        # For development/testing mode when Shopify credentials aren't available
        should_use_mock = (
            not settings.shopify_token
            or settings.environment.lower() in ["dev", "test"]
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

        logger.info(f"🚀 SHOPIFY REST API REQUEST - {method} {endpoint}")
        logger.info(f"🔗 Endpoint: {full_url}")
        logger.info(f"🔑 Headers: {self.headers}")
        if data:
            logger.info(f"📤 Request Data: {json.dumps(data, indent=2)}")

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

            # Enhanced response logging
            logger.info(f"📥 SHOPIFY REST API RESPONSE - {method} {endpoint}")
            logger.info(f"📊 Status Code: {response.status_code}")
            logger.info(f"📈 Response Headers: {dict(response.headers)}")

            # Log response size
            content_length = response.headers.get("content-length", "unknown")
            logger.info(f"📏 Response Size: {content_length} bytes")

            # Handle different HTTP status codes
            if response.status_code == 401:
                logger.error("🚨 Shopify authentication error (401): Invalid API token")
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

            logger.info(f"✅ SHOPIFY REST API SUCCESS - {method} {endpoint}")
            logger.info(f"📤 Full Response: {json.dumps(result, indent=2)}")
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

        logger.info(f"🔧 Updating variant {numeric_id} via REST API...")
        logger.info(f"📦 Update data: {variant_data}")

        response = self._make_shopify_rest_request(endpoint, "PUT", payload)

        if response and "variant" in response:
            logger.info(f"✅ Variant {numeric_id} updated successfully")
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
