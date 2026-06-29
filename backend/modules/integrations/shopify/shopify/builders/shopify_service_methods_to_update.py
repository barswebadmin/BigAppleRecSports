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

        query = build_adjust_inventory_mutation(
            inventory_item_id=inventory_item_id,
            delta=delta,
            location_id=location_id,
            reference_uri=reference_uri,
        )

        data = self.shopify_client.send_request(query).raw

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
    


# ----- END PRODUCT / INVENTORY REQUESTS -----

