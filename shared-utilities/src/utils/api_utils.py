"""
Common API Helper Functions
Converted from GAS apiUtils.gs for Python usage
"""

import json
import time
import logging
import requests
from typing import Dict, Any, Optional, Callable, Union

logger = logging.getLogger(__name__)


def make_api_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Union[str, Dict[str, Any]]] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Make a secure API request with proper error handling

    Args:
        url: The API endpoint URL
        method: HTTP method (GET, POST, PUT, DELETE)
        headers: Request headers
        payload: Request payload (string or dict)
        timeout: Request timeout in seconds

    Returns:
        Parsed response or error object
    """
    default_headers = {"Content-Type": "application/json"}

    if headers:
        default_headers.update(headers)

    try:
        logger.info(f"Making {method} request to: {url}")

        # Prepare payload
        if payload and isinstance(payload, dict):
            payload = json.dumps(payload)

        response = requests.request(
            method=method.upper(),
            url=url,
            headers=default_headers,
            data=payload,
            timeout=timeout,
        )

        logger.info(f"Response code: {response.status_code}")

        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.info("Response is not JSON, returning as text")
                return {"success": True, "data": response.text}
        else:
            logger.error(
                f"API request failed with code {response.status_code}: {response.text}"
            )
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "message": response.text,
            }

    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        return {
            "success": False,
            "error": "Request timeout",
            "message": f"Request timed out after {timeout} seconds",
        }
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return {"success": False, "error": "Connection error", "message": str(e)}
    except Exception as e:
        logger.error(f"API request failed: {e}")
        return {"success": False, "error": "Request failed", "message": str(e)}


def build_shopify_graphql_request(
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    shopify_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build Shopify GraphQL request options

    Args:
        query: GraphQL query string
        variables: GraphQL variables
        shopify_token: Shopify access token

    Returns:
        Request options for API call
    """
    if not shopify_token:
        # Try to get from environment or raise error
        import os

        shopify_token = os.getenv("SHOPIFY_TOKEN")
        if not shopify_token:
            raise ValueError("SHOPIFY_TOKEN is required")

    return {
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": shopify_token,
        },
        "payload": {"query": query, "variables": variables or {}},
    }


def retry_api_request(
    request_function: Callable[[], Dict[str, Any]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Dict[str, Any]:
    """
    Retry an API request with exponential backoff

    Args:
        request_function: Function that makes the API request
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds
        backoff_factor: Exponential backoff factor

    Returns:
        API response or final error
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = request_function()

            # If successful, return immediately
            if result and result.get("success") is not False:
                return result

            last_error = result
        except Exception as e:
            last_error = {
                "success": False,
                "error": "Request failed",
                "message": str(e),
            }

        # If this wasn't the last attempt, wait before retrying
        if attempt < max_retries:
            delay = base_delay * (backoff_factor**attempt)
            logger.info(
                f"Request failed, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})"
            )
            time.sleep(delay)

    logger.error(f"All {max_retries + 1} attempts failed")
    return last_error


def capitalize(text: str) -> str:
    """
    Capitalize the first letter of a string

    Args:
        text: String to capitalize

    Returns:
        Capitalized string
    """
    if not text:
        return text
    return text[0].upper() + text[1:]


def format_two_decimal_points(raw_amount: Union[str, int, float]) -> str:
    """
    Format number to two decimal places

    Args:
        raw_amount: Number to format

    Returns:
        Formatted number string
    """
    try:
        return f"{float(raw_amount):.2f}"
    except (ValueError, TypeError):
        return "0.00"


def normalize_order_number(order_number: Union[str, int, None]) -> str:
    """
    Normalize order number to include # prefix

    Args:
        order_number: Order number to normalize

    Returns:
        Normalized order number with # prefix
    """
    if order_number is None:
        return "#"

    str_number = str(order_number).strip()
    return str_number if str_number.startswith("#") else f"#{str_number}"


def make_shopify_api_request(
    url: str,
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    shopify_token: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Make a Shopify GraphQL API request

    Args:
        url: Shopify GraphQL endpoint URL
        query: GraphQL query string
        variables: GraphQL variables
        shopify_token: Shopify access token
        timeout: Request timeout

    Returns:
        API response
    """
    request_options = build_shopify_graphql_request(query, variables, shopify_token)

    return make_api_request(
        url=url,
        method=request_options["method"],
        headers=request_options["headers"],
        payload=request_options["payload"],
        timeout=timeout,
    )


def handle_api_response(
    response: Dict[str, Any], expected_keys: Optional[list] = None
) -> Dict[str, Any]:
    """
    Handle and validate API response

    Args:
        response: API response dictionary
        expected_keys: List of expected keys in successful response

    Returns:
        Processed response with validation
    """
    if not isinstance(response, dict):
        return {
            "success": False,
            "error": "Invalid response format",
            "message": "Response is not a dictionary",
        }

    # Check if response indicates success
    if response.get("success") is False:
        return response

    # Check for expected keys if provided
    if expected_keys:
        missing_keys = []
        for key in expected_keys:
            if key not in response:
                missing_keys.append(key)

        if missing_keys:
            return {
                "success": False,
                "error": "Missing expected response keys",
                "message": f'Missing keys: {", ".join(missing_keys)}',
                "original_response": response,
            }

    return response


def build_webhook_payload(
    event_type: str, data: Dict[str, Any], timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build a standardized webhook payload

    Args:
        event_type: Type of event being sent
        data: Event data
        timestamp: Event timestamp (ISO format)

    Returns:
        Standardized webhook payload
    """
    from datetime import datetime

    if not timestamp:
        timestamp = datetime.now().isoformat()

    return {
        "event_type": event_type,
        "timestamp": timestamp,
        "data": data,
        "version": "1.0",
    }


def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with fallback

    Args:
        json_string: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """
    Safely serialize object to JSON string with fallback

    Args:
        obj: Object to serialize
        default: Default JSON string if serialization fails

    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize to JSON: {e}")
        return default
