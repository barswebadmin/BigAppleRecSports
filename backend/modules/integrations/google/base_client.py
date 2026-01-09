"""
Base Google API Client.

Handles common authentication and transport logic for all Google API clients.
"""

import logging
from typing import Optional, Dict, Any, NoReturn, List, Callable, Tuple, TypeVar, cast
from abc import ABC, abstractmethod
from functools import wraps

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest
import json

from backend.config import config

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


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
    def wrapper(self: 'GoogleAPIClient', *args: Any, **kwargs: Any) -> Any:
        try:
            return func(self, *args, **kwargs)
        except HttpError as e:
            self._raise_for_status(e)
    
    return cast(F, wrapper)


class GoogleAPIClient(ABC):
    """Base client for Google API authentication and common transport."""
    
    service: Any
    scopes: List[str]
    base_credentials: service_account.Credentials
    credentials: service_account.Credentials
    
    def __init__(
        self,
        service_account_info: Optional[Dict[str, Any]] = None,
        subject: Optional[str] = None
    ):
        """
        Initialize Google API client with service account credentials.
        
        Args:
            service_account_info: Service account JSON dict.
                                If None, uses config.GOOGLE.SERVICE_ACCOUNT.
            subject: Email address of the user to impersonate (for domain-wide delegation).
                    If None, uses service account directly.
        
        Raises:
            ValueError: If credentials are missing or invalid
        """
        service_account_info = self._get_service_account_info(service_account_info)
        scopes = self._get_scopes()
        
        try:
            self.base_credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=scopes
            )
            
            if subject:
                self.credentials = self.base_credentials.with_subject(subject)
                logger.info(f"✅ Using domain-wide delegation with subject: {subject}")
            else:
                self.credentials = self.base_credentials
            
            logger.info(
                f"✅ {self.__class__.__name__} initialized with service account: "
                f"{self.base_credentials.service_account_email}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            raise ValueError(f"Invalid Google service account credentials: {e}")
    
    @staticmethod
    def _get_service_account_info(
        service_account_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Load service account info from config if not provided."""
        if service_account_info is not None:
            return service_account_info
        
        google_config = getattr(config, 'GOOGLE', None)
        if not google_config or not hasattr(google_config, 'SERVICE_ACCOUNT'):
            raise ValueError(
                "Google service account credentials not found in config. "
                "Please ensure google-service-account.json exists in the backend/ directory."
            )
        return getattr(google_config, 'SERVICE_ACCOUNT')
    
    def _get_scopes(self) -> List[str]:
        """Return list of OAuth scopes required for this API."""
        return self.scopes
    
    def _build_service(self, service_name: str, version: str) -> Any:
        """Build and return the Google API service instance."""
        return build(service_name, version, credentials=self.credentials)
    
    @property
    def service_account_email(self) -> str:
        """Get the service account email address."""
        return self.base_credentials.service_account_email
    
    def _paginate_api_call(
        self,
        api_method,
        result_key: str,
        **params: Any
    ) -> List[Any]:
        """
        Generic pagination helper for Google API calls.
        
        Args:
            api_method: The API method to call (e.g., self.service.members().list)
            result_key: The key in the response containing the list of items (e.g., 'members', 'groups')
            **params: Additional parameters to pass to the API method
        
        Returns:
            List of all items from all pages
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
    
    def batch_request(
        self,
        requests: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple API requests in a single batch HTTP request.
        
        Args:
            requests: List of prepared API request objects (e.g., service.members().list(...))
                     Each request should be a callable that returns a request object.
                     Maximum 1,000 requests per batch.
        
        Returns:
            List of response dictionaries in the same order as requests.
            Each response is the result of calling .execute() on the request.
        
        Raises:
            ValueError: If more than 1,000 requests provided
            HttpError: If batch request fails
        
        Example:
            >>> client = GoogleDirectoryClient(subject="admin@example.com")
            >>> requests = [
            ...     client.service.members().list(groupKey='group1@example.com'),
            ...     client.service.members().list(groupKey='group2@example.com'),
            ... ]
            >>> responses = client.batch_request(requests)
            >>> for response in responses:
            ...     print(response.get('members', []))
        """
        if len(requests) > 50:
            raise ValueError(f"Maximum 50 requests per batch. Got {len(requests)} requests.")
        
        responses: Dict[str, Dict[str, Any]] = {}
        errors: Dict[str, Exception] = {}
        request_order: List[str] = []
        
        def batch_callback(request_id: str, response: Any, exception: Optional[Exception]) -> None:
            """Callback for batch request responses."""
            request_order.append(request_id)
            if exception:
                errors[request_id] = exception
            else:
                responses[request_id] = response
        
        batch = self.service.new_batch_http_request(callback=batch_callback)
        
        for idx, request in enumerate(requests):
            request_id = str(idx)
            batch.add(request, request_id=request_id)
        
        batch.execute()
        
        # Reconstruct responses in order
        ordered_responses: List[Dict[str, Any]] = []
        for request_id in request_order:
            if request_id in errors:
                raise errors[request_id]
            ordered_responses.append(responses[request_id])
        
        logger.info(f"✅ Executed batch request with {len(requests)} requests")
        
        return ordered_responses
    
    def _raise_for_status(
        self,
        error: HttpError
    ) -> NoReturn:
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

