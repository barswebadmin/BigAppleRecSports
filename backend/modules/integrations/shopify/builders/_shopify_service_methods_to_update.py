# ----- CUSTOMER REQUESTS -----

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

        data = self.shopify_client.send_request({"query": query}).raw

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

        # Initialize Shopify session (legacy, skip if SDK not available)
        if shopify is None:
            raise RuntimeError("Shopify Python SDK not available")

        # Fetch customer
        if customer_id:
            cust = shopify.Customer.find(customer_id) if shopify else None
            # Some versions return None when not found
            if not cust or not getattr(cust, "id", None):
                msg = f"Customer not found for id: {customer_id}"
                print(f"📭 {msg}")
                logger.info(msg)
                return {"success": True, "message": "No customer found", "customer": None}
        else:
            results = shopify.Customer.search(query=f"email:{customer_email}") if shopify else []
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


# ----- END CUSTOMER REQUESTS -----


# ----- PRODUCT / INVENTORY REQUESTS -----


# Inventory management methods
def get_inventory_item_and_quantity(self, variant_gid: str) -> Dict[str, Any]:
    """Get inventory item ID and available quantity for a given variant GID"""
    try:
        query = build_get_inventory_item_and_quantity(variant_gid)

        data = self.shopify_client.send_request(query).raw

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
        result = self.shopify_client.send_request(payload).raw

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

    


# ----- END PRODUCT / INVENTORY REQUESTS -----


# ----- REFUND REQUESTS -----
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

def cancel_order(self, order_id: str) -> Dict[str, Any]:
    return shopify_order_utils.cancel_order(order_id, self.shopify_client.send_request)

def create_refund(
    self, order_id: str, refund_amount: float, refund_type: str = "refund"
) -> Dict[str, Any]:
    return shopify_order_utils.create_refund(
        order_id, refund_amount, refund_type, self.shopify_client.send_request
    )

# ----- END REFUND REQUESTS -----

