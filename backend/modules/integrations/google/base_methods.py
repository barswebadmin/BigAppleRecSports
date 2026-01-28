"""
Base methods for Google API clients.

Contains common authentication, error handling, and transport logic
shared across all Google API services.
"""

import logging
import json
import sys
from typing import Optional, Dict, Any, NoReturn, Callable, TypeVar, cast, TypedDict
from functools import wraps

from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from backend.shared.model_config import ApiModel

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def _handle_refresh_error(error: RefreshError, required_scopes: Optional[list[str]] = None, service_name: Optional[str] = None) -> NoReturn:
    """
    Handle RefreshError exceptions that occur during credential refresh.
    
    Provides detailed scope authorization diagnostics to help users fix the issue.
    
    Args:
        error: RefreshError from Google auth library
        required_scopes: Optional list of scopes that were requested
        service_name: Optional name of the service that failed (for diagnostics)
    
    Raises:
        RefreshError: Re-raises the original RefreshError after logging diagnostics
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    # Extract error details if available
    # RefreshError typically has error details in error.args[1] as a dict
    error_details = {}
    if hasattr(error, 'args') and len(error.args) > 1:
        if isinstance(error.args[1], dict):
            error_details = error.args[1]
    
    logger.error(f"Credential refresh error: {error_type}: {error_msg}", exc_info=True)
    
    print(f"[ERROR] ========== SCOPE AUTHORIZATION ERROR ==========", file=sys.stderr)
    if service_name:
        print(f"[ERROR] Service: {service_name}", file=sys.stderr)
    print(f"[ERROR] Error Type: {error_type}", file=sys.stderr)
    print(f"[ERROR] Error Message: {error_msg}", file=sys.stderr)
    print(f"[ERROR] ", file=sys.stderr)
    
    if required_scopes:
        print(f"[ERROR] REQUESTED SCOPES ({len(required_scopes)} total):", file=sys.stderr)
        for i, scope in enumerate(required_scopes, 1):
            print(f"[ERROR]   {i}. {scope}", file=sys.stderr)
        print(f"[ERROR] ", file=sys.stderr)
        print(f"[ERROR] 💡 TIP: Run 'python -m backend.modules.integrations.google.test_scopes' to test", file=sys.stderr)
        print(f"[ERROR]    which scopes are actually authorized for this service account.", file=sys.stderr)
        print(f"[ERROR] ", file=sys.stderr)
    
    # Check for unauthorized_client error
    if 'unauthorized_client' in error_msg.lower():
        print(f"[ERROR] ❌ UNAUTHORIZED CLIENT ERROR", file=sys.stderr)
        print(f"[ERROR] ", file=sys.stderr)
        print(f"[ERROR] This means the service account is not authorized for the requested scopes.", file=sys.stderr)
        print(f"[ERROR] ", file=sys.stderr)
        print(f"[ERROR] TO FIX:", file=sys.stderr)
        print(f"[ERROR] 1. Go to Google Admin Console: https://admin.google.com", file=sys.stderr)
        print(f"[ERROR] 2. Navigate: Security > API Controls > Domain-wide Delegation", file=sys.stderr)
        print(f"[ERROR] 3. Find your service account (check the service account email in the logs above)", file=sys.stderr)
        if required_scopes:
            print(f"[ERROR] 4. Add the following scopes (one per line):", file=sys.stderr)
            for scope in required_scopes:
                print(f"[ERROR]    {scope}", file=sys.stderr)
        else:
            print(f"[ERROR] 4. Add the required scopes for this API", file=sys.stderr)
        print(f"[ERROR] 5. Ensure domain-wide delegation is enabled for this service account", file=sys.stderr)
    else:
        print(f"[ERROR] Common causes:", file=sys.stderr)
        print(f"[ERROR]   1. Domain-wide delegation not enabled in Google Admin Console", file=sys.stderr)
        if required_scopes:
            print(f"[ERROR]   2. Required scopes not granted to service account", file=sys.stderr)
        print(f"[ERROR]   3. Service account credentials are invalid or expired", file=sys.stderr)
        print(f"[ERROR]   4. Service account doesn't have necessary permissions", file=sys.stderr)
    
    if error_details:
        print(f"[ERROR] ", file=sys.stderr)
        print(f"[ERROR] Error details:", file=sys.stderr)
        print(f"[ERROR] {json.dumps(error_details, indent=2)}", file=sys.stderr)
    
    print(f"[ERROR] =========================================================", file=sys.stderr)
    
    raise


def handle_http_errors(func: F) -> F:
    """
    Decorator to automatically handle HttpError and RefreshError exceptions in Google API client methods.
    
    Catches HttpError and RefreshError, calls appropriate error handlers to log and re-raise,
    ensuring consistent error handling across all API methods without requiring try/except blocks.
    
    Automatically passes required_scopes to error handler if available on the service instance.
    
    Usage:
        @handle_http_errors
        def my_api_method(self, ...):
            return self.service.some().method().execute()
    """
    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        service_name = getattr(self, '__class__', type(self)).__name__
        method_name = func.__name__
        
        try:
            return func(self, *args, **kwargs)
        except RefreshError as e:
            # Handle credential refresh errors (scope authorization issues)
            required_scopes = getattr(self, 'required_scopes', None)
            _handle_refresh_error(e, required_scopes=required_scopes, service_name=service_name)
        except (TimeoutError, OSError) as e:
            # Handle timeout and network errors
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Check if this is happening during credential refresh
            import traceback
            tb_str = ''.join(traceback.format_exc())
            is_credential_refresh = 'refresh' in tb_str.lower() or 'before_request' in tb_str.lower()
            
            print(f"[ERROR] ========== TIMEOUT/NETWORK ERROR ==========", file=sys.stderr)
            print(f"[ERROR] Service: {service_name}", file=sys.stderr)
            print(f"[ERROR] Method: {method_name}", file=sys.stderr)
            print(f"[ERROR] Error Type: {error_type}", file=sys.stderr)
            print(f"[ERROR] Error Message: {error_msg}", file=sys.stderr)
            if is_credential_refresh:
                print(f"[ERROR] ", file=sys.stderr)
                print(f"[ERROR] ⚠️ This timeout occurred during credential refresh (not the API call itself)", file=sys.stderr)
                print(f"[ERROR]    The credentials are trying to get an access token from Google's OAuth2 endpoint.", file=sys.stderr)
            print(f"[ERROR] ", file=sys.stderr)
            print(f"[ERROR] This is a network connectivity or timeout issue.", file=sys.stderr)
            print(f"[ERROR] ", file=sys.stderr)
            print(f"[ERROR] Possible causes:", file=sys.stderr)
            print(f"[ERROR]   1. Network connectivity issues (firewall, VPN, proxy)", file=sys.stderr)
            print(f"[ERROR]   2. Google API service temporarily unavailable", file=sys.stderr)
            print(f"[ERROR]   3. httplib2 timeout too short (default may be very short)", file=sys.stderr)
            print(f"[ERROR]   4. DNS resolution problems", file=sys.stderr)
            print(f"[ERROR]   5. Intermittent network issue (curl works, but Python httplib2 times out)", file=sys.stderr)
            print(f"[ERROR] ", file=sys.stderr)
            print(f"[ERROR] Try:", file=sys.stderr)
            print(f"[ERROR]   - Retry the operation (may be intermittent)", file=sys.stderr)
            print(f"[ERROR]   - Check internet connectivity: curl https://oauth2.googleapis.com/token", file=sys.stderr)
            print(f"[ERROR]   - Check firewall/proxy settings", file=sys.stderr)
            print(f"[ERROR]   - Check if other services can refresh credentials successfully", file=sys.stderr)
            print(f"[ERROR] =========================================================", file=sys.stderr)
            
            logger.error(f"Timeout/Network error in {service_name}.{method_name}: {e}", exc_info=True)
            raise
        except HttpError as e:
            # Get required_scopes from service instance if available
            required_scopes = getattr(self, 'required_scopes', None)
            if hasattr(self, '_raise_for_status'):
                # If service has custom _raise_for_status, use it (it should handle scopes)
                self._raise_for_status(e, required_scopes=required_scopes)
            else:
                # Fallback to global raise_for_status
                raise_for_status(e, required_scopes=required_scopes)
    
    return cast(F, wrapper)


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


def raise_for_status(error: HttpError, required_scopes: Optional[list[str]] = None) -> NoReturn:
    """
    Centralized error handling for Google API HTTP errors.
    
    Converts HttpError to JSON and logs it, then re-raises the original HttpError.
    Detects and reports insufficient scope errors when scopes are provided.
    
    Args:
        error: HttpError from Google API
        required_scopes: Optional list of scopes that were requested for this API call
    
    Raises:
        HttpError: Re-raises the original HttpError after logging JSON representation
    """
    import sys
    
    error_dict = {
        'status_code': error.resp.status,
        'reason': error.reason,
        'error_details': error.error_details,
        'uri': error.uri,
        'content': error.content.decode('utf-8') if error.content else None
    }
    
    error_content = error_dict.get('content', '')
    error_reason = error_dict.get('reason', '')
    status_code = error_dict.get('status_code', 0)
    
    # Detect scope-related errors
    is_scope_error = False
    scope_indicators = [
        'insufficient permissions',
        'insufficient scope',
        'access denied',
        'permission denied',
        'forbidden',
        'unauthorized',
        'scope',
        '403'
    ]
    
    error_text = f"{error_reason} {error_content}".lower()
    if status_code == 403 or any(indicator in error_text for indicator in scope_indicators):
        is_scope_error = True
    
    logger.error(
        f"Google API error:\n{json.dumps(error_dict, indent=2)}"
    )
    
    # Print scope diagnostics if this appears to be a scope error
    if is_scope_error and required_scopes:
        print(f"[ERROR] ========== INSUFFICIENT SCOPE ERROR DETECTED ==========", file=sys.stderr)
        print(f"[ERROR] Status Code: {status_code}", file=sys.stderr)
        print(f"[ERROR] Error: {error_reason}", file=sys.stderr)
        print(f"[ERROR] ", file=sys.stderr)
        print(f"[ERROR] The API method attempted requires scopes that were not authorized.", file=sys.stderr)
        print(f"[ERROR] ", file=sys.stderr)
        print(f"[ERROR] REQUESTED SCOPES ({len(required_scopes)} total):", file=sys.stderr)
        for i, scope in enumerate(required_scopes, 1):
            print(f"[ERROR]   {i}. {scope}", file=sys.stderr)
        print(f"[ERROR] ", file=sys.stderr)
        print(f"[ERROR] TO FIX:", file=sys.stderr)
        print(f"[ERROR] 1. Go to Google Admin Console: https://admin.google.com", file=sys.stderr)
        print(f"[ERROR] 2. Navigate: Security > API Controls > Domain-wide Delegation", file=sys.stderr)
        print(f"[ERROR] 3. Find your service account and ensure ALL scopes above are authorized", file=sys.stderr)
        print(f"[ERROR] 4. The API endpoint attempted: {error_dict.get('uri', 'Unknown')}", file=sys.stderr)
        if error_content:
            print(f"[ERROR] ", file=sys.stderr)
            print(f"[ERROR] Error details from Google:", file=sys.stderr)
            try:
                error_json = json.loads(error_content)
                print(f"[ERROR] {json.dumps(error_json, indent=2)}", file=sys.stderr)
            except:
                print(f"[ERROR] {error_content[:500]}", file=sys.stderr)
        print(f"[ERROR] =========================================================", file=sys.stderr)
    
    raise
