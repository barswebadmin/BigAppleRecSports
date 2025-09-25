from typing import Dict, Any, Optional, List
from typing import Any  # for type ignore casts if needed
import logging
from config import config

# ShopifyAPI exposes a dynamic top-level "shopify" package without type hints.
# Import via module to avoid brittle symbol re-exports across versions.
import shopify  # type: ignore
logger = logging.getLogger(__name__)

"""
ShopifyClient - thin wrapper over ShopifyAPI SDK with typed helper methods.
"""

def get_order_details(order_id: Optional[str] = None, order_number: Optional[str] = None) -> Dict[str, Any]:
    """Get order details from Shopify using the Python SDK where possible.

    - If order_id (GID or numeric) is provided, fetch via REST resource find.
    - If order_number (Shopify name, e.g., "#12345") is provided, try SDK search first,
      then fall back to the REST endpoint with name filter if SDK search is unavailable.
    Returns a normalized dict: { "success": bool, "order": dict | None, "message"?: str }
    """
    if not order_id and not order_number:
        return {"success": False, "message": "Either order_id or order_number must be provided"}

    # Fetch by ID (supports numeric ID or full GID)
    if order_id:
        try:
            # Extract numeric ID if a GID was provided
            numeric_id = order_id.split("/")[-1] if order_id.startswith("gid://") else order_id
            order_obj = shopify.Order.find(numeric_id)  # type: ignore
            if not order_obj:
                logger.info("🧭 SDK:get_order_by_id → not found")
                return {"success": True, "order": None, "message": "Order not found"}
            # ActiveResource sometimes returns a list for find
            if isinstance(order_obj, list):
                order_obj = order_obj[0] if order_obj else None
            if not order_obj:
                logger.info("🧭 SDK:get_order_by_id → not found (empty list)")
                return {"success": True, "order": None, "message": "Order not found"}
            logger.info("🧭 SDK:get_order_by_id → found")
            return {"success": True, "order": order_obj.to_dict() if hasattr(order_obj, "to_dict") else getattr(order_obj, "attributes", {})}
        except Exception as e:
            logger.warning(f"🧭 SDK:get_order_by_id → error: {e}")
            return {"success": False, "message": f"Order fetch by id failed: {e}"}

    # Normalize order number with leading '#'
    name = order_number or ""
    if name and not name.startswith("#"):
        name = f"#{name}"

    # First try SDK search helpers
    try:
        results: Optional[List[Any]] = None
        if hasattr(shopify.Order, "search"):
            # Graph-like search API provided for some resources
            logger.info(f"🧭 SDK:get_order_by_name via .search name={name}")
            results = shopify.Order.search(query=f"name:{name}")  # type: ignore
        else:
            # Fallback to generic ActiveResource search
            # Some SDK versions support: find(from_='search', q='name:#12345')
            try:
                logger.info(f"🧭 SDK:get_order_by_name via .find(from_='search') name={name}")
                results = shopify.Order.find(from_="search", q=f"name:{name}")  # type: ignore
            except Exception:
                logger.info("🧭 SDK:get_order_by_name .find(from_='search') unavailable")
                results = None

        if results:
            order_obj = results[0]
            logger.info("🧭 SDK:get_order_by_name → found")
            return {"success": True, "order": order_obj.to_dict() if hasattr(order_obj, "to_dict") else getattr(order_obj, "attributes", {})}
    except Exception:
        # ignore and fallback
        logger.info("🧭 SDK:get_order_by_name → error; will fallback")
        pass

    # Final fallback: REST endpoint filter by name (SDK wrapper via .find may not expose it)
    try:
        # ActiveResource find with params
        logger.info(f"🧭 SDK:get_order_by_name via .find(name=...) fallback name={name}")
        orders: List[Any] = shopify.Order.find(limit=1, name=name)  # type: ignore
        if orders:
            order_obj = orders[0]
            logger.info("🧭 SDK:get_order_by_name fallback → found")
            return {"success": True, "order": order_obj.to_dict() if hasattr(order_obj, "to_dict") else getattr(order_obj, "attributes", {})}
        logger.info("🧭 SDK:get_order_by_name fallback → not found")
        return {"success": True, "order": None, "message": "Order not found"}
    except Exception as e:
        logger.warning(f"🧭 SDK:get_order_by_name fallback → error: {e}")
        return {"success": False, "message": f"Order search by name failed: {e}"}

# ----------------------------------------------------------------------------
# Class-based SDK wrapper (requested structure)
# ----------------------------------------------------------------------------

class ShopifyClient:
    @classmethod
    def _initialize_session(cls, shop_url: str, api_version: str, access_token: str) -> None:
        session = shopify.Session(shop_url, api_version, access_token)  # type: ignore
        shopify.ShopifyResource.activate_session(session)  # type: ignore
    def __init__(self, shop_url: Optional[str] = None, api_version: Optional[str] = None, access_token: Optional[str] = None) -> None:
        """
        Initialize and authenticate a Shopify SDK session.

        Defaults:
        - shop_url: f"{config.Shopify.store_id}.myshopify.com"
        - api_version: $SHOPIFY_API_VERSION or "2025-07"
        - access_token: config.Shopify.token
        """
        resolved_shop_url = shop_url or f"{config.Shopify.store_id}.myshopify.com"
        # Prefer passed api_version else config (derive version from config URLs if you later add it), fallback to default
        resolved_api_version = api_version or "2025-07"
        resolved_token = access_token or config.Shopify.token
        logger.info(
            f"🧭 SDK:initialize_session shop={resolved_shop_url} api_version={resolved_api_version}"
        )
        type(self)._initialize_session(resolved_shop_url, resolved_api_version, resolved_token)

    class Order:
        @staticmethod
        def get(params: Dict[str, Optional[str]]) -> Any:
            """
            Get order using Shopify SDK Order.find()/search variants.

            params: {
              "order_id"?: str,           # numeric ID
              "order_gid"?: str,          # gid://shopify/Order/12345
              "order_number"?: str        # Shopify order name, e.g., "#12345" or "12345"
            }

            Returns whatever shopify.Order.find/search returns (un-normalized),
            per request.
            """
            order_id = params.get("order_id")
            order_gid = params.get("order_gid")
            order_number = params.get("order_number")

            # Prefer ID if provided; normalize gid → numeric
            if order_gid and not order_id:
                try:
                    order_id = order_gid.split("/")[-1]
                except Exception:
                    pass

            if order_id:
                logger.info(f"🧭 SDK:Order.get by id={order_id}")
                return shopify.Order.find(order_id)  # type: ignore

            if order_number:
                name = order_number if order_number.startswith("#") else f"#{order_number}"
                # Try search if available
                if hasattr(shopify.Order, "search"):
                    logger.info(f"🧭 SDK:Order.get by name via search name={name}")
                    return shopify.Order.search(query=f"name:{name}")  # type: ignore
                # Fallback to ActiveResource search endpoint then name filter
                try:
                    logger.info(f"🧭 SDK:Order.get by name via find(from_='search') name={name}")
                    return shopify.Order.find(from_="search", q=f"name:{name}")  # type: ignore
                except Exception:
                    logger.info(f"🧭 SDK:Order.get by name via find(name=...) fallback name={name}")
                    return shopify.Order.find(limit=1, name=name)  # type: ignore

            raise ValueError("Provide one of order_id, order_gid, or order_number")

# def make_shopify_request(request_details: Dict[str, Any]) -> Dict[str, Any]:
#     """Make a Shopify request"""
#     response = requests.post(
#                 self.graphql_url,
#                 headers=self.headers,
#                 json=query,
#                 timeout=30,
#                 verify=True,  # Use system certificates
#             )