import requests
import json
import logging
from typing import Optional, Dict, Any
import sys
import os

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
        self.graphql_url = settings.graphql_url
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": settings.shopify_token
        }
    
    def _make_request(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
    
    def get_customer_id(self, email: str) -> Optional[str]:
        """Get customer ID by email address (deprecated - use get_customer_with_tags)"""
        customer = self.get_customer_with_tags(email)
        return customer["id"] if customer else None
    
    def get_customer_with_tags(self, email: str) -> Optional[Dict[str, Any]]:
        """Get customer ID and existing tags by email address"""
        query = {
            "query": """
                query GetCustomerWithTags($identifier: CustomerIdentifierInput!) {
                    customerByIdentifier(identifier: $identifier) { 
                        id 
                        tags
                    }
                }
            """,
            "variables": {
                "identifier": {
                    "emailAddress": email
                }
            }
        }
        
        result = self._make_request(query)
        if result and result.get("data", {}).get("customerByIdentifier"):
            customer_data = result["data"]["customerByIdentifier"]
            return {
                "id": customer_data["id"],
                "tags": customer_data.get("tags", [])
            }
        return None
    
    def add_tag_to_customer(self, customer_id: str, tag: str, existing_tags: Optional[list] = None) -> bool:
        """Add a tag to a customer's existing tags (appends, doesn't replace)"""
        if existing_tags is None:
            existing_tags = []
        
        # Combine existing tags with new tag, remove duplicates, and convert to comma-separated string
        all_tags = list(set(existing_tags + [tag]))
        tags_string = ', '.join(all_tags)
        
        mutation = {
            "query": """
                mutation updateCustomerTags($input: CustomerInput!) { 
                    customerUpdate(input: $input) { 
                        customer { 
                            id 
                            tags 
                        } 
                        userErrors { 
                            message 
                            field 
                        } 
                    } 
                }
            """,
            "variables": {
                "input": {
                    "id": customer_id,
                    "tags": tags_string
                }
            }
        }
        
        result = self._make_request(mutation)
        if result and result.get("data", {}).get("customerUpdate"):
            errors = result["data"]["customerUpdate"].get("userErrors", [])
            if not errors:
                return True
            else:
                print(f"Error adding tag to customer {customer_id}: {errors}")
        return False
    
    def get_customers_batch(self, emails: list) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get multiple customers with their tags in batch (up to 10 at a time)"""
        batch_results = {}
        
        # Process in batches of 10 (Shopify GraphQL limit consideration)
        batch_size = 10
        for i in range(0, len(emails), batch_size):
            batch_emails = emails[i:i + batch_size]
            
            # Build query for batch
            query_parts = []
            variables = {}
            
            for j, email in enumerate(batch_emails):
                alias = f"customer_{j}"
                query_parts.append(f"""
                    {alias}: customerByIdentifier(identifier: {{emailAddress: "{email}"}}) {{
                        id
                        tags
                        email
                    }}
                """)
            
            query = {
                "query": f"""
                    query GetCustomersBatch {{
                        {' '.join(query_parts)}
                    }}
                """
            }
            
            result = self._make_request(query)
            if result and result.get("data"):
                for j, email in enumerate(batch_emails):
                    alias = f"customer_{j}"
                    customer_data = result["data"].get(alias)
                    
                    if customer_data:
                        batch_results[email] = {
                            "id": customer_data["id"],
                            "tags": customer_data.get("tags", [])
                        }
                    else:
                        batch_results[email] = None
                        
        return batch_results
    
    def create_segment(self, name: str, query: str) -> Optional[str]:
        """Create a customer segment"""
        mutation = {
            "query": """
                mutation segmentCreate($name: String!, $query: String!) { 
                    segmentCreate(name: $name, query: $query) { 
                        segment { 
                            id 
                        } 
                        userErrors { 
                            field 
                            message 
                        } 
                    } 
                }
            """,
            "variables": {
                "name": name,
                "query": query
            }
        }
        
        result = self._make_request(mutation)
        if result and result.get("data", {}).get("segmentCreate", {}).get("segment"):
            return result["data"]["segmentCreate"]["segment"]["id"]
        return None
    
    def create_discount_code(self, code: str, usage_limit: int, season: str, 
                           year: int, segment_id: str, discount_amount: float) -> bool:
        """Create a discount code for a specific season and segment"""
        try:
            from utils.date_utils import get_season_start_and_end
        except ImportError:
            from backend.utils.date_utils import get_season_start_and_end
        
        start_date, end_date = get_season_start_and_end(season, year)
        
        mutation = {
            "query": """
                mutation CreateDiscountCode($basicCodeDiscount: DiscountCodeBasicInput!) {
                    discountCodeBasicCreate(basicCodeDiscount: $basicCodeDiscount) {
                        codeDiscountNode { 
                            id 
                        }
                        userErrors { 
                            message 
                        }
                    }
                }
            """,
            "variables": {
                "basicCodeDiscount": {
                    "title": code,
                    "code": code,
                    "startsAt": start_date,
                    "endsAt": end_date,
                    "customerSelection": {
                        "customerSegments": {
                            "add": [segment_id]
                        }
                    },
                    "customerGets": {
                        "value": {
                            "percentage": discount_amount
                        },
                        "items": {
                            "all": True
                        }
                    },
                    "appliesOncePerCustomer": usage_limit == 1
                }
            }
        }
        
        result = self._make_request(mutation)
        if result and result.get("data", {}).get("discountCodeBasicCreate"):
            errors = result["data"]["discountCodeBasicCreate"].get("userErrors", [])
            if not errors:
                return True
            else:
                print(f"Error creating discount code {code}: {errors}")
        return False 

    def test_connection(self) -> bool:
        """Test the Shopify connection"""
        try:
            query = {
                "query": "{ shop { name } }"
            }
            result = self._make_request(query)
            return result is not None and "data" in result
        except Exception:
            return False

    async def adjust_shopify_inventory(self, variant_id: str, delta: int = 1) -> Dict[str, Any]:
        """Adjust Shopify inventory using the GraphQL API"""
        try:
            if settings.is_debug_mode:
                # Debug mode - return mock success without API call
                print(f"🧪 DEBUG MODE: Would adjust inventory for variant {variant_id} by {delta}")
                
                # Mock GraphQL mutation for debug purposes
                mutation_body = {
                    "query": """
                        mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
                            inventoryAdjustQuantities(input: $input) {
                                userErrors { field message }
                                inventoryAdjustmentGroup {
                                    createdAt
                                    reason
                                    changes { name delta }
                                }
                            }
                        }
                    """,
                    "variables": {
                        "input": {
                            "reason": "movement_created",
                            "name": "available", 
                            "changes": [
                                {
                                    "delta": delta,
                                    "inventoryItemId": "mock_inventory_item_id",
                                    "locationId": "gid://shopify/Location/61802217566"
                                }
                            ]
                        }
                    }
                }
                
                print(f"🧪 DEBUG MODE: Would send GraphQL mutation:\n{json.dumps(mutation_body, indent=2)}")
                return {"success": True, "message": "Mock inventory adjustment in debug mode"}
                
            else:
                # Production mode - make actual Shopify GraphQL API call
                print(f"🏭 PRODUCTION MODE: Making real inventory adjustment for variant {variant_id}")
                
                # Step 1: Fetch variant details to get inventory item ID (like Google Apps Script)
                variant_query = {
                    "query": """
                        query getVariant($id: ID!) {
                            productVariant(id: $id) {
                                id
                                title
                                inventoryItem {
                                    id
                                }
                            }
                        }
                    """,
                    "variables": {
                        "id": variant_id
                    }
                }
                
                print(f"🔍 Fetching variant details for {variant_id}")
                
                variant_response = requests.post(
                    self.graphql_url,
                    headers=self.headers,
                    json=variant_query,
                    timeout=30
                )
                
                if variant_response.status_code != 200:
                    error_msg = f"Failed to fetch variant details: HTTP {variant_response.status_code}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}
                
                variant_result = variant_response.json()
                
                if "errors" in variant_result:
                    error_msg = f"GraphQL errors fetching variant: {variant_result['errors']}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}
                
                variant_data = variant_result.get("data", {}).get("productVariant")
                if not variant_data or not variant_data.get("inventoryItem", {}).get("id"):
                    error_msg = f"No inventory item found for variant {variant_id}"
                    logger.error(error_msg)
                    return {"success": False, "message": error_msg}
                
                inventory_item_id = variant_data["inventoryItem"]["id"]
                variant_title = variant_data.get("title", "Unknown")
                print(f"✅ Found inventory item ID: {inventory_item_id} for variant: {variant_title}")
                
                # Step 2: Adjust inventory using the correct inventory item ID
                inventory_mutation = {
                    "query": """
                        mutation inventoryAdjustQuantities($input: InventoryAdjustQuantitiesInput!) {
                            inventoryAdjustQuantities(input: $input) {
                                userErrors { field message }
                                inventoryAdjustmentGroup {
                                    createdAt
                                    reason
                                    changes { name delta }
                                }
                            }
                        }
                    """,
                    "variables": {
                        "input": {
                            "reason": "movement_created",
                            "name": "available", 
                            "changes": [
                                {
                                    "delta": delta,
                                    "inventoryItemId": inventory_item_id,
                                    "locationId": "gid://shopify/Location/61802217566"
                                }
                            ]
                        }
                    }
                }
                
                # Make the actual GraphQL API call to Shopify
                print(f"🏭 PRODUCTION MODE: Sending inventory adjustment mutation to {self.graphql_url}")
                response = requests.post(
                    self.graphql_url,
                    headers=self.headers,
                    json=inventory_mutation,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check for GraphQL errors
                    if "errors" in result:
                        error_msg = f"GraphQL errors: {result['errors']}"
                        logger.error(f"Shopify GraphQL errors during inventory adjustment: {error_msg}")
                        return {"success": False, "message": error_msg}
                    
                    # Check for user errors in the mutation response
                    data = result.get("data", {})
                    inventory_adjust = data.get("inventoryAdjustQuantities", {})
                    user_errors = inventory_adjust.get("userErrors", [])
                    
                    if user_errors:
                        error_msg = f"Inventory adjustment user errors: {user_errors}"
                        logger.error(f"Shopify inventory adjustment user errors: {error_msg}")
                        return {"success": False, "message": error_msg}
                    
                    # Success case
                    adjustment_group = inventory_adjust.get("inventoryAdjustmentGroup", {})
                    logger.info(f"✅ Successfully adjusted inventory for variant {variant_id} by {delta}")
                    return {
                        "success": True, 
                        "message": "Inventory adjusted successfully",
                        "adjustment_group": adjustment_group
                    }
                    
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"Failed to adjust Shopify inventory: {error_msg}")
                    return {"success": False, "message": error_msg}
            
        except Exception as e:
            logger.error(f"Error adjusting Shopify inventory: {e}")
            return {"success": False, "message": str(e)} 