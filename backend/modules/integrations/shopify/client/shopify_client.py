from typing import Dict, Any, Optional, List, Union, cast
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import config

from modules.products.models import FetchProductRequest
from modules.orders.models import FetchOrderRequest
from ..models.responses import ShopifyResponse, ShopifyResponseKind
from ..parsers import parse_shopify_response
from ..builders import build_product_fetch_request_payload, build_order_fetch_request_payload
from ..parsers.mappers import map_order_node_to_order

 
"""
ShopifyClient - HTTP client using requests to interact with Shopify GraphQL with retries/timeouts.
"""
class ShopifyClient:
    def __init__(self) -> None:
        self.config = config.shopify
        self.url = self.config.graphql_url
        self.headers = self.config.headers
        self.max_retries = self.config.max_retries
        self.timeout_seconds = self.config.timeout_seconds

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------
    def post_graphql_safe(self, body: Dict[str, Any]) -> requests.Response:
        """POST to Shopify GraphQL with retries and timeout using config settings."""
        
        # Debug: Print the actual URL being used (remove in production)
        # print(f"[SHOPIFY_CLIENT_DEBUG] Making request to: {url}")

        # Set SSL certificate path for macOS with Homebrew
        import os
        ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
        verify_ssl = ssl_cert_file if os.path.exists(ssl_cert_file) else True

        last_exc: Optional[Exception] = None
        for _ in range(self.max_retries):
            try:
                return requests.post(self.url, json=body, headers=self.headers, timeout=self.timeout_seconds, verify=verify_ssl)
            except requests.Timeout as e:
                # Bubble up timeouts immediately; they shouldn't be retried blindly
                raise TimeoutError(f"Shopify request timeout after {self.timeout_seconds}s") from e
            except requests.RequestException as e:
                last_exc = e
                continue
        # Retries exhausted
        if last_exc:
            raise last_exc
        raise RuntimeError("Unexpected transport error")

    def send_request(self, payload: Dict[str, Any]) -> ShopifyResponse:
        body = {"query": payload.get("query"), "variables": payload.get("variables", {})}
        if not body.get("query"): 
            raise ValueError("Error sending Shopify request: missing GraphQL query")

        resp = self.post_graphql_safe(body)
        status = resp.status_code
        # Try to parse JSON body; if not JSON, keep text
        parsed: Any
        try:
            parsed = resp.json()
        except Exception:
            parsed = {"text": resp.text}

        if status == 404:
            return ShopifyResponse.Error(
                kind=ShopifyResponseKind.NOT_FOUND, 
                errors=parsed.get("errors")
            )  

        if status == 401:
            # Success → return parsed response with original status
            return ShopifyResponse.Error(
                kind=ShopifyResponseKind.UNAUTHORIZED, 
                errors=parsed.get("errors")
            )

        if status >= 500:
            msg = str(parsed.get("errors") if isinstance(parsed, dict) else resp.text)
            return ShopifyResponse.Error(
                kind=ShopifyResponseKind.SERVER_ERROR, 
                errors=msg
            )

        try:
            return parse_shopify_response(parsed)
        except Exception as e:
            return ShopifyResponse.Error(
                kind=ShopifyResponseKind.UNEXPECTED_ERROR, 
                errors=str(e)
            )


    # def send_batch_requests(self, payloads: List[Dict[str, Any]]) -> List[ShopifyResponse]:
    #     """Parallel fan-out of multiple single-operation calls."""
    #     if not payloads:
    #         return []
    #     results: List[ShopifyResponse] = [ShopifyResponse.Error(message="Pending", status_code=500)] * len(payloads)
    #     with ThreadPoolExecutor(max_workers=min(8, len(payloads))) as pool:
    #         futures = {pool.submit(self.send_request, payloads[i]): i for i in range(len(payloads))}
    #         for fut in as_completed(futures):
    #             idx = futures[fut]
    #             try:
    #                 results[idx] = fut.result()
    #             except Exception as e:
    #                 results[idx] = ShopifyResponse.Error(message=str(e), status_code=500)
    #     return results

    # ------------------------------------------------------------------
    # Instance methods
    # ------------------------------------------------------------------
    

    