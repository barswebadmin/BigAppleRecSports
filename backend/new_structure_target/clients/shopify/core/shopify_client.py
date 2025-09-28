from typing import Dict, Any, Optional, List, Union, cast
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import config
from backend.models.shopify.requests import FetchOrderRequest
from backend.models.shopify.responses import ShopifyResponse
from ..builders.shopify_request_builders import build_order_fetch_request_payload
from ..mappers import map_order_node_to_order

 

"""
ShopifyClient - HTTP client using requests to interact with Shopify GraphQL with retries/timeouts.
"""


class ShopifyClient:
    def __init__(self, *, timeout_seconds: int = 10, max_retries: int = 3) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._url = config.Shopify.graphql_url
        self._headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": config.Shopify.token,
        }

    def send_request(self, payload: Dict[str, Any]) -> ShopifyResponse:
        body = {"query": payload.get("query"), "variables": payload.get("variables", {})}
        if not body.get("query"):
            return ShopifyResponse.from_error("Missing GraphQL query", 400)

        last_error: Optional[str] = None
        for _ in range(self._max_retries):
            try:
                resp = requests.post(self._url, json=body, headers=self._headers, timeout=self._timeout_seconds)
                status = resp.status_code
                # Try to parse JSON body; if not JSON, keep text
                parsed: Any
                try:
                    parsed = resp.json()
                except Exception:
                    parsed = {"text": resp.text}

                if status < 300:
                    # Success → return parsed response with original status
                    return ShopifyResponse.from_graphql(parsed if isinstance(parsed, dict) else {}, status)

                if 400 <= status < 500:
                    # Client error → return structured error (do not raise)
                    msg = str(parsed.get("errors") if isinstance(parsed, dict) else resp.text)
                    return ShopifyResponse.from_error(msg, status)

                # Server error (>=500) → raise
                raise RuntimeError(f"Shopify server error {status}: {resp.text[:200]}")

            except requests.Timeout as e:
                # Propagate timeouts to caller
                raise TimeoutError(f"Shopify request timeout after {self._timeout_seconds}s") from e
            except requests.RequestException as e:
                # Network/transport errors – try again, then raise after retries
                last_error = f"{type(e).__name__}: {str(e)}"
                continue
            except Exception as e:
                # Unexpected exceptions – fail fast
                raise

        # Retries exhausted on transport errors
        message = last_error or "Unexpected transport error"
        raise RuntimeError(message)

    def send_batch_requests(self, payloads: List[Dict[str, Any]]) -> List[ShopifyResponse]:
        """Parallel fan-out of multiple single-operation calls."""
        if not payloads:
            return []
        results: List[ShopifyResponse] = [ShopifyResponse.from_error("Pending", 500)] * len(payloads)
        with ThreadPoolExecutor(max_workers=min(8, len(payloads))) as pool:
            futures = {pool.submit(self.send_request, payloads[i]): i for i in range(len(payloads))}
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    results[idx] = fut.result()
                except Exception as e:
                    results[idx] = ShopifyResponse.from_error(str(e), 500)
        return results

    # ------------------------------------------------------------------
    # Instance methods
    # ------------------------------------------------------------------
    def fetch_order_details(
        self,
        *,
        request_args: FetchOrderRequest
    ) -> ShopifyResponse:
        """
        Fetch order details with a single request: prefer order_id if provided,
        otherwise use order_number. Callers must validate inputs.
        """
        # Build query from identifier (order number, order id, or email)
       
        payload = build_order_fetch_request_payload(request_args)

        resp = self.send_request(payload)
        return resp

    