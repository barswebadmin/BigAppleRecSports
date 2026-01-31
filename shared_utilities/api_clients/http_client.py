"""
Minimal HTTP client wrapper around HTTPX with tenacity retries.

Leverages HTTPX's built-in features instead of reimplementing them.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx
from decorator import decorator
from tenacity import (
    retry as retry_with_tenacity,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

logger = logging.getLogger(__name__)


# Simple exceptions
class HTTPClientError(httpx.RequestError):
    """HTTP client error"""


class RateLimitError(HTTPClientError):
    """Rate limit exceeded"""


@dataclass
class RetryPolicy:
    """Retry configuration"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    retryable_status_codes: list[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    retryable_exceptions: tuple = field(default_factory=lambda: (
        httpx.ConnectError,
        httpx.TimeoutException,
        httpx.NetworkError,
        httpx.ProtocolError,
    ))


def with_retry(retry_policy: RetryPolicy):
    """Clean retry decorator using the decorator library."""
    
    @decorator
    def retry_wrapper(func, *args, **kwargs):
        # Create the tenacity retry decorator
        retrying_func = retry_with_tenacity(
            stop=stop_after_attempt(retry_policy.max_retries + 1),
            wait=wait_exponential(
                multiplier=retry_policy.base_delay,
                max=retry_policy.max_delay,
                exp_base=retry_policy.backoff_factor
            ),
            retry=retry_if_exception_type(retry_policy.retryable_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.DEBUG)
        )(func)
        
        return retrying_func(*args, **kwargs)
    
    return retry_wrapper


class SyncHTTPClient(httpx.Client):
    """
    HTTPX Client with automatic retries and smart header management.
    
    Inherits all HTTPX Client functionality and adds tenacity retry logic.
    Headers are built from individual components rather than a monolithic headers dict.
    """
    
    # Expose exceptions as class attributes for easy access
    HTTPClientError = HTTPClientError
    RateLimitError = RateLimitError

    def __init__(
        self, 
        retry_policy: Optional[RetryPolicy] = None, 
        auth: Optional[dict] = None,
        content_type: Optional[str] = None,
        accept: Optional[str] = None,
        user_agent: Optional[str] = None,
        custom_headers: Optional[dict] = None,
        **kwargs
    ):
        # Build headers from components
        headers = {}
        
        # Set defaults
        headers['Content-Type'] = content_type or 'application/json'
        headers['Accept'] = accept or 'application/json'
        headers['User-Agent'] = user_agent or 'bars-cli/1.0.0'
        
        # Add auth if provided
        if auth:
            if 'username' in auth and 'password' in auth:
                import base64
                credentials = f"{auth['username']}:{auth['password']}"
                encoded_credentials = base64.b64encode(credentials.encode()).decode()
                headers['Authorization'] = f"Basic {encoded_credentials}"
            elif 'token' in auth:
                headers['Authorization'] = f"Bearer {auth['token']}"
            elif 'authorization' in auth:
                headers['Authorization'] = auth['authorization']
        
        # Add any custom headers (these can overwrite the above)
        if custom_headers:
            headers.update(custom_headers)
        
        # Pass headers to parent constructor
        super().__init__(headers=headers, **kwargs)
        self.retry_policy = retry_policy or RetryPolicy()

    def _check_response(self, response: httpx.Response) -> None:
        """Check response and raise exceptions for retryable errors"""
        if response.status_code in self.retry_policy.retryable_status_codes:
            if response.status_code == 429:
                raise RateLimitError(f"Rate limit exceeded: HTTP {response.status_code}")
            raise HTTPClientError(f"HTTP {response.status_code}: {response.text}")

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make request with retries - clean and simple!"""
        
        @with_retry(self.retry_policy)
        def _make_request():
            response = super(SyncHTTPClient, self).request(method, url, **kwargs)
            self._check_response(response)
            return response

        try:
            return _make_request()
        except Exception as e:
            if isinstance(e, (HTTPClientError, RateLimitError)):
                raise
            raise HTTPClientError(f"Request failed: {str(e)}") from e


class AsyncHTTPClient(httpx.AsyncClient):
    """
    HTTPX AsyncClient with automatic retries and smart header management.
    
    Inherits all HTTPX AsyncClient functionality and adds tenacity retry logic.
    Headers are built from individual components rather than a monolithic headers dict.
    """
    
    # Expose exceptions as class attributes for easy access
    HTTPClientError = HTTPClientError
    RateLimitError = RateLimitError

    def __init__(
        self, 
        retry_policy: Optional[RetryPolicy] = None, 
        auth: Optional[dict] = None,
        content_type: Optional[str] = None,
        accept: Optional[str] = None,
        user_agent: Optional[str] = None,
        custom_headers: Optional[dict] = None,
        **kwargs
    ):
        # Build headers from components
        headers = {}
        
        # Set defaults
        headers['Content-Type'] = content_type or 'application/json'
        headers['Accept'] = accept or 'application/json'
        headers['User-Agent'] = user_agent or 'bars-cli/1.0.0'
        
        # Add auth if provided
        if auth:
            if 'username' in auth and 'password' in auth:
                import base64
                credentials = f"{auth['username']}:{auth['password']}"
                encoded_credentials = base64.b64encode(credentials.encode()).decode()
                headers['Authorization'] = f"Basic {encoded_credentials}"
            elif 'token' in auth:
                headers['Authorization'] = f"Bearer {auth['token']}"
            elif 'authorization' in auth:
                headers['Authorization'] = auth['authorization']
        
        # Add any custom headers (these can overwrite the above)
        if custom_headers:
            headers.update(custom_headers)
        
        # Pass headers to parent constructor
        super().__init__(headers=headers, **kwargs)
        self.retry_policy = retry_policy or RetryPolicy()

    def _check_response(self, response: httpx.Response) -> None:
        """Check response and raise exceptions for retryable errors"""
        if response.status_code in self.retry_policy.retryable_status_codes:
            if response.status_code == 429:
                raise RateLimitError(f"Rate limit exceeded: HTTP {response.status_code}")
            raise HTTPClientError(f"HTTP {response.status_code}: {response.text}")

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make async request with retries - clean and simple!"""
        
        @with_retry(self.retry_policy)
        async def _make_request():
            response = await super(AsyncHTTPClient, self).request(method, url, **kwargs)
            self._check_response(response)
            return response

        try:
            return await _make_request()
        except Exception as e:
            if isinstance(e, (HTTPClientError, RateLimitError)):
                raise
            raise HTTPClientError(f"Request failed: {str(e)}") from e
