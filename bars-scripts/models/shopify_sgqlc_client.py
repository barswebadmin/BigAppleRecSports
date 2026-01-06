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

# Import from shared_utils for environment/config loading
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_utils import load_environment, get_shopify_config


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
            # Load environment and get config
            load_environment(environment)
            config = get_shopify_config(environment)
        
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

