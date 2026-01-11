"""
Base methods for Google API clients.

Contains common authentication, error handling, and transport logic
shared across all Google API services.
"""

import logging
import json
from typing import Optional, Dict, Any, NoReturn, Callable, TypeVar, cast, TypedDict
from functools import wraps

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.config import config

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


class GoogleServiceAccountInfo(TypedDict, total=False):
    """Google service account JSON structure.
    
    All fields are strings. The 'subject' field is optional (for domain-wide delegation).
    """
    type: str  # 'service_account'
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    auth_uri: str
    token_uri: str
    auth_provider_x509_cert_url: str
    client_x509_cert_url: str
    universe_domain: str
    subject: str  # Optional - for domain-wide delegation


def handle_http_errors(func: F) -> F:
    """
    Decorator to automatically handle HttpError exceptions in Google API client methods.
    
    Catches HttpError, calls _raise_for_status to log and re-raise, ensuring consistent
    error handling across all API methods without requiring try/except blocks.
    
    Usage:
        @handle_http_errors
        def my_api_method(self, ...):
            return self.service.some().method().execute()
    """
    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return func(self, *args, **kwargs)
        except HttpError as e:
            self._raise_for_status(e)
    
    return cast(F, wrapper)


def get_service_account_info(
    service_account_info: Optional[GoogleServiceAccountInfo]
) -> GoogleServiceAccountInfo:
    """Load service account info from config if not provided."""
    if service_account_info is not None:
        if not isinstance(service_account_info, dict):
            raise ValueError(
                f"service_account_info must be a dict, got {type(service_account_info).__name__}"
            )
        return service_account_info
    
    google_config = getattr(config, 'GOOGLE', None)
    if not google_config:
        raise ValueError(
            "Google service account credentials not found in config. "
            "Please ensure google-service-account.json exists in the backend/ directory."
        )
    
    if not hasattr(google_config, 'SERVICE_ACCOUNT'):
        raise ValueError(
            "Google service account credentials not found in config.GOOGLE. "
            "Please ensure google-service-account.json exists in the backend/ directory."
        )
    
    service_account: Optional[GoogleServiceAccountInfo] = getattr(google_config, 'SERVICE_ACCOUNT')
    
    if service_account is None:
        raise ValueError(
            "Google service account credentials are None in config.GOOGLE.SERVICE_ACCOUNT. "
            "Please ensure google-service-account.json exists in the backend/ directory and is valid JSON."
        )
    
    if not isinstance(service_account, dict):
        raise ValueError(
            f"Google service account credentials must be a dict, got {type(service_account).__name__}. "
            "Please check that google-service-account.json contains valid JSON."
        )
    
    return service_account


def initialize_credentials(
    service_account_info: Optional[GoogleServiceAccountInfo],
    scopes: list[str],
    subject: Optional[str] = None
) -> tuple[service_account.Credentials, service_account.Credentials]:
    """
    Initialize Google service account credentials.
    
    Args:
        service_account_info: Service account JSON dict. If None, uses config.
        scopes: List of OAuth scopes required
        subject: Email address of the user to impersonate (for domain-wide delegation)
    
    Returns:
        Tuple of (base_credentials, credentials)
    """
    service_account_info = get_service_account_info(service_account_info)
    
    # Get subject from parameter first, then fall back to service_account_info dict
    if subject is None and isinstance(service_account_info, dict):
        subject = service_account_info.get("subject", None)
    
    # Pass subject directly to from_service_account_info (this works, with_subject() doesn't)
    base_credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        subject=subject,
        scopes=scopes
    )
    credentials = base_credentials
    
    if subject:
        logger.info(f"✅ Using domain-wide delegation with subject: {subject}")
    else:
        logger.warning("⚠️ No subject provided - using service account directly (may have limited permissions)")
    
    return base_credentials, credentials


def build_service(service_name: str, version: str, credentials: service_account.Credentials) -> Any:
    """Build and return the Google API service instance."""
    return build(service_name, version, credentials=credentials)


def paginate_api_call(
    api_method: Any,
    result_key: str,
    **params: Any
) -> list[Any]:
    """
    Generic pagination helper for Google API calls.
    
    Args:
        api_method: The API method to call (e.g., self.service.members().list)
        result_key: The key in the response containing the list of items (e.g., 'members', 'groups')
        **params: Additional parameters to pass to the API method
    
    Returns:
        list of all items from all pages
    """
    all_items = []
    page_token = None
    
    while True:
        if page_token:
            params['pageToken'] = page_token
        
        result = api_method(**params).execute()
        items = result.get(result_key, [])
        all_items.extend(items)
        
        page_token = result.get('nextPageToken')
        if not page_token:
            break
    
    return all_items


def execute_batch_request(
    service: Any,
    requests: list[Any]
) -> list[Dict[str, Any]]:
    """
    Execute multiple API requests in a single batch HTTP request.
    
    Args:
        service: Google API service instance with new_batch_http_request method
        requests: list of prepared API request objects (e.g., service.members().list(...))
                 Each request should be a callable that returns a request object.
                 Maximum 50 requests per batch.
    
    Returns:
        list of response dictionaries in the same order as requests.
        Each response is the result of calling .execute() on the request.
    
    Raises:
        ValueError: If more than 50 requests provided
        HttpError: If batch request fails
    
    Example:
        >>> requests = [
        ...     service.members().list(groupKey='group1@example.com'),
        ...     service.members().list(groupKey='group2@example.com'),
        ... ]
        >>> responses = execute_batch_request(service, requests)
        >>> for response in responses:
        ...     print(response.get('members', []))
    """
    if len(requests) > 50:
        raise ValueError(f"Maximum 50 requests per batch. Got {len(requests)} requests.")
    
    responses: Dict[str, Dict[str, Any]] = {}
    errors: Dict[str, Exception] = {}
    request_order: list[str] = []
    
    def batch_callback(request_id: str, response: Any, exception: Optional[Exception]) -> None:
        """Callback for batch request responses."""
        request_order.append(request_id)
        if exception:
            errors[request_id] = exception
        else:
            responses[request_id] = response
    
    batch = service.new_batch_http_request(callback=batch_callback)
    
    for idx, request in enumerate(requests):
        request_id = str(idx)
        batch.add(request, request_id=request_id)
    
    batch.execute()
    
    # Reconstruct responses in order
    ordered_responses: list[Dict[str, Any]] = []
    for request_id in request_order:
        if request_id in errors:
            raise errors[request_id]
        ordered_responses.append(responses[request_id])
    
    logger.info(f"✅ Executed batch request with {len(requests)} requests")
    
    return ordered_responses


def raise_for_status(error: HttpError) -> NoReturn:
    """
    Centralized error handling for Google API HTTP errors.
    
    Converts HttpError to JSON and logs it, then re-raises the original HttpError.
    
    Args:
        error: HttpError from Google API
    
    Raises:
        HttpError: Re-raises the original HttpError after logging JSON representation
    """
    error_dict = {
        'status_code': error.resp.status,
        'reason': error.reason,
        'error_details': error.error_details,
        'uri': error.uri,
        'content': error.content.decode('utf-8') if error.content else None
    }
    
    logger.error(
        f"Google API error:\n{json.dumps(error_dict, indent=2)}"
    )
    
    raise
