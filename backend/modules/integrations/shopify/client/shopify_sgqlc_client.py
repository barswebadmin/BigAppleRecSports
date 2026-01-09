"""
Shopify GraphQL Client using sgqlc.

Provides a generic client interface for executing GraphQL queries and mutations
against the Shopify Admin API using sgqlc operations.
"""

import json
from typing import Dict, Any, Optional
import urllib.error
import sys
from pathlib import Path
from sgqlc.operation import Operation
from sgqlc.endpoint.http import HTTPEndpoint

# Import from backend config
backend_path = Path(__file__).parent.parent.parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
from config import config as global_config  # type: ignore[import-untyped]


class ShopifySGQLCClient:
    """Generic client for executing Shopify GraphQL operations using sgqlc.
    
    This client is domain-agnostic and handles only HTTP execution.
    Domain-specific query building should be done in models/query builders.
    
    The client automatically loads environment variables and Shopify configuration
    based on the specified environment.
    """
    
    def __init__(self, environment: str = "production", config: Optional[Dict[str, Any]] = None):
        """Initialize client with Shopify API configuration.
        
        Args:
            environment: Environment name ("production", "staging", or "development").
                Defaults to "production". Used to load environment variables and
                determine which Shopify credentials to use.
            config: Optional pre-configured Shopify API configuration dict. If provided,
                environment loading is skipped and this config is used directly.
                Should have:
                - graphql_url: GraphQL endpoint URL
                - headers: HTTP headers dict (must include Authorization)
        
        Raises:
            RuntimeError: If environment loading fails or required credentials are missing
        """
        if config is None:
            # Get config from global config singleton
            env = environment.lower()
            # Type ignore: global_config is a global singleton, not None
            shopify_config = getattr(global_config, 'SHOPIFY', None)  # type: ignore[attr-defined]
            
            if env in ["staging", "production"]:
                # Access nested structure: SHOPIFY.STORE_ID, SHOPIFY.TOKEN.ADMIN, etc.
                store_id = None
                token = None
                
                if shopify_config:
                    store_id = getattr(shopify_config, "STORE_ID", None) or getattr(shopify_config, "STORE", None)
                    # Handle nested TOKEN namespace: SHOPIFY.TOKEN.ADMIN
                    token_obj = getattr(shopify_config, "TOKEN", None)
                    if token_obj:
                        token = (
                            getattr(token_obj, "ADMIN", None) or
                            getattr(token_obj, "WRITE_ORDERS_READ_PRODUCTS_CUSTOMERS", None)
                        )
                
                # Fallback to direct env var access (handles SHOPIFY.TOKEN.ADMIN format)
                import os
                if not store_id:
                    store_id = os.getenv("SHOPIFY_STORE_ID") or os.getenv("SHOPIFY_STORE") or os.getenv("SHOPIFY.STORE_ID")
                if not token:
                    # Try multiple formats: SHOPIFY.TOKEN.ADMIN, SHOPIFY_TOKEN_ADMIN, etc.
                    token = (
                        os.getenv("SHOPIFY.TOKEN.ADMIN") or
                        os.getenv("SHOPIFY.TOKEN.WRITE_ORDERS_READ_PRODUCTS_CUSTOMERS") or
                        os.getenv("SHOPIFY_TOKEN_ADMIN") or
                        os.getenv("SHOPIFY_TOKEN") or
                        os.getenv("SHOPIFY_TOKEN_WRITE_ORDERS_READ_PRODUCTS_CUSTOMERS")
                    )
            else:
                # Development environment
                store_id = None
                token = None
                
                if shopify_config:
                    store_id = getattr(shopify_config, "DEV_STORE_ID", None) or getattr(shopify_config, "DEV_STORE", None)
                    token = getattr(shopify_config, "DEV_TOKEN", None)
                
                # Fallback to direct env var access
                if not store_id or not token:
                    import os
                    store_id = store_id or os.getenv("SHOPIFY_DEV_STORE_ID") or os.getenv("SHOPIFY_DEV_STORE")
                    token = token or os.getenv("SHOPIFY_DEV_TOKEN")
            
            if not store_id or not token:
                raise RuntimeError(f"Missing Shopify credentials for environment: {env}")
            
            config = {
                "store_id": store_id,
                "token": token,
                "graphql_url": f"https://{store_id}.myshopify.com/admin/api/2025-07/graphql.json",
                "headers": {
                    "Content-Type": "application/json",
                    "X-Shopify-Access-Token": token,
                }
            }
        
        self.config = config
        self.environment = environment
        self.endpoint = HTTPEndpoint(
            config["graphql_url"],
            base_headers=config["headers"].copy(),
            timeout=30
        )
    
    def execute(self, operation: Operation) -> Dict[str, Any]:
        """Execute a GraphQL operation and return the GraphQL response body.
        
        This method is generic and works with any sgqlc Operation.
        It returns the GraphQL response (data, errors, extensions) excluding HTTP metadata.
        Only raises exceptions for HTTP/network errors.
        
        Args:
            operation: The sgqlc Operation object to execute
        
        Returns:
            GraphQL response dict with structure:
            {
                "data": {...},      # Present if query succeeded
                "errors": [...],    # Present if GraphQL errors occurred
                "extensions": {...} # Optional metadata
            }
            Note: Both "data" and "errors" may be present in the same response.
            HTTP headers are excluded from the response.
        
        Raises:
            RuntimeError: If the HTTP request fails (non-200 status, network errors, timeouts)
                This does NOT raise for GraphQL errors - those are returned in the response.
        """
        try:
            response_data = self.endpoint(operation)
        except urllib.error.HTTPError as e:
            # HTTPError is raised for non-200 status codes
            status = getattr(e, 'code', 'unknown')
            reason = getattr(e, 'reason', str(e))
            raise RuntimeError(
                f"Shopify API request failed with status {status}: {reason}"
            ) from e
        except Exception as e:
            # Catch any other exceptions (network errors, timeouts, etc.)
            raise RuntimeError(f"Shopify API request failed: {str(e)}") from e
        
        # Return full GraphQL response (data, errors, extensions)
        # Filter out HTTP metadata (headers) - only return GraphQL response body
        graphql_response = {
            key: value 
            for key, value in response_data.items() 
            if key in ('data', 'errors', 'extensions')
        }
        
        return graphql_response

