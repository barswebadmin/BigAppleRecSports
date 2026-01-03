from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import time
from urllib3.exceptions import NameResolutionError
from requests.exceptions import ConnectionError, Timeout

from modules.integrations.slack.client.users_client import SlackUsersClient

logger = logging.getLogger(__name__)


def _is_transient_error(exception: Exception) -> bool:
    """
    Check if an exception is a transient error that should be retried.
    
    Args:
        exception: The exception to check
        
    Returns:
        True if the error is transient and should be retried
    """
    # DNS resolution errors
    if isinstance(exception, NameResolutionError):
        return True
    
    # Connection errors and timeouts
    if isinstance(exception, (ConnectionError, Timeout)):
        return True
    
    # Check for specific error messages
    error_str = str(exception).lower()
    transient_indicators = [
        "failed to resolve",
        "connection refused",
        "connection reset",
        "connection timeout",
        "read timeout",
        "rate limit",
        "429",
        "502",
        "503",
        "504"
    ]
    
    return any(indicator in error_str for indicator in transient_indicators)


def _retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 0.5):
    """
    Retry a function with exponential backoff for transient errors.
    
    Args:
        func: The function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (doubles with each retry)
        
    Returns:
        The result of the function call
        
    Raises:
        The last exception if all retries fail
    """
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                # Final attempt failed, re-raise
                raise
            
            if not _is_transient_error(e):
                # Not a transient error, don't retry
                raise
            
            logger.warning(
                f"Transient error on attempt {attempt + 1}/{max_retries + 1}: {e}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            delay *= 2  # Exponential backoff


class UserLookupService:
    """Service for looking up Slack user IDs from email addresses."""
    
    def __init__(self, token: str):
        self.client = SlackUsersClient(token)
    
    def lookup_user_ids_by_emails(
        self, 
        emails: List[str], 
        max_workers: int = 10,
        max_retries: int = 3
    ) -> Dict[str, Optional[str]]:
        """
        Look up Slack user IDs for multiple email addresses concurrently with retry logic.
        
        Args:
            emails: List of email addresses to look up
            max_workers: Maximum number of concurrent API requests (default: 10)
            max_retries: Maximum retry attempts for transient errors (default: 3)
            
        Returns:
            Dictionary mapping email to user ID (or None if not found)
            Example: {"john@example.com": "U12345ABC", "notfound@example.com": None}
        """
        results: Dict[str, Optional[str]] = {}
        
        if not emails:
            return results
        
        logger.info(f"Looking up {len(emails)} email(s) with {max_workers} concurrent workers and {max_retries} max retries")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_email = {
                executor.submit(self._lookup_single_email, email, max_retries): email
                for email in emails
            }
            
            for future in as_completed(future_to_email):
                email = future_to_email[future]
                try:
                    user_id = future.result()
                    results[email] = user_id
                    if user_id:
                        logger.debug(f"✓ Found user ID for {email}")
                    else:
                        logger.debug(f"✗ No user found for {email}")
                except Exception as e:
                    logger.error(f"Unexpected error looking up {email}: {e}")
                    results[email] = None
        
        found_count = sum(1 for uid in results.values() if uid)
        logger.info(f"Lookup complete: {found_count}/{len(emails)} users found")
        
        return results
    
    def _lookup_single_email(self, email: str, max_retries: int = 3) -> Optional[str]:
        """
        Look up a single email address with retry logic for transient errors.
        
        Args:
            email: Email address to look up
            max_retries: Maximum number of retry attempts for transient errors
            
        Returns:
            Slack user ID if found, None otherwise
        """
        def _do_lookup():
            user = self.client.lookup_by_email(email)
            if user:
                return user.get("id")
            return None
        
        try:
            return _retry_with_backoff(_do_lookup, max_retries=max_retries)
        except Exception as e:
            logger.error(f"Failed to lookup {email} after {max_retries} retries: {e}")
            return None

