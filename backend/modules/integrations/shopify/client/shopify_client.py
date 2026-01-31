"""
ShopifyClient - HTTP client using HTTPX to interact with Shopify GraphQL with retries/timeouts.
"""

from typing import Dict, Any

from shared_utilities.api_clients.http_client import SyncHTTPClient, RetryPolicy
from config import config
from ..models.requests import FetchOrderRequest
from ..models.responses import ShopifyResponse, ShopifyResponseKind
from ..parsers import parse_shopify_response


class ShopifyClient(SyncHTTPClient):
    """Shopify GraphQL client with centralized HTTP error handling and retries."""

    def __init__(self) -> None:
        self._config = config['SHOPIFY']
        self._token = self._config['TOKEN']['ADMIN']

        retry_policy = RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            retryable_status_codes=[429, 500, 502, 503, 504]
        )

        super().__init__(
            base_url=self._config['URL']['API_GRAPH_QL'],
            content_type="application/json",
            custom_headers={"X-Shopify-Access-Token": self._token},
            retry_policy=retry_policy,
            timeout=10.0
        )

        self._admin_url = self._config['URL']['ADMIN']
        self._graphql_url = self._config['URL']['API_GRAPH_QL']
        self._store_id = self._config['STORE_ID']
        self._location_id = self._config['LOCATION_ID']

    def send_request(self, payload: Dict[str, Any]) -> ShopifyResponse:
        """Send GraphQL request to Shopify with automatic retries."""
        body = {"query": payload.get("query"), "variables": payload.get("variables", {})}
        if not body.get("query"):
            raise ValueError("Error sending Shopify request: missing GraphQL query")

        try:
            # Use inherited HTTP client with automatic retries
            resp = self.post("/", json=body)
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

            return parse_shopify_response(parsed)
        except Exception as e:
            return ShopifyResponse.Error(
                kind=ShopifyResponseKind.UNEXPECTED_ERROR,
                errors=str(e)
            )

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
        # DEPRECATED: This method should be migrated to use sgqlc via ShopifyService
        # payload = build_order_fetch_request_payload(request_args)
        # resp = self.send_request(payload)
        # return resp
        raise NotImplementedError(
            "fetch_order_details is deprecated. "
            "Use ShopifyService.get_order_by_identifier() instead."
        )