from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ShopifyCustomerUtils:
    def __init__(self, request_func):
        self._make_shopify_request = request_func
    
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
        
        result = self._make_shopify_request(query)
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
        
        result = self._make_shopify_request(mutation)
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
            
            result = self._make_shopify_request(query)
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
        
        result = self._make_shopify_request(mutation)
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
        
        result = self._make_shopify_request(mutation)
        if result and result.get("data", {}).get("discountCodeBasicCreate"):
            errors = result["data"]["discountCodeBasicCreate"].get("userErrors", [])
            if not errors:
                return True
            else:
                print(f"Error creating discount code {code}: {errors}")
        return False 

