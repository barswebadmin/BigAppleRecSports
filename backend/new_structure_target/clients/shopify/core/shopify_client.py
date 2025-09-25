from typing import Dict, Any
from typing import Any  # for type ignore casts if needed

# ShopifyAPI exposes a dynamic top-level "shopify" package without type hints.
# Import concrete symbols and silence Pyright's attr resolution complaints.
from shopify import Session, ShopifyResource

# Placeholder client wrapper for future use
def initialize_shopify_session(shop_url: str, api_version: str, access_token: str) -> None:
    session = Session(shop_url, api_version, access_token)
    ShopifyResource.activate_session(session)

# def make_shopify_request(request_details: Dict[str, Any]) -> Dict[str, Any]:
#     """Make a Shopify request"""
#     response = requests.post(
#                 self.graphql_url,
#                 headers=self.headers,
#                 json=query,
#                 timeout=30,
#                 verify=True,  # Use system certificates
#             )