from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from slack_sdk import WebClient

from modules.integrations.slack.client import SlackClient
from modules.integrations.slack.models.slack_user import SlackUser

logger = logging.getLogger(__name__)


class UserLookupService:
    """Service for looking up Slack users by email addresses."""
    
    def __init__(self, token: str):
        self.slack_client = SlackClient()
        self.slack_client.client = WebClient(token=token)
    
    @staticmethod
    def normalize_email(email: str) -> str:
        """
        Normalize email address for consistent lookups.
        
        Args:
            email: Raw email address
            
        Returns:
            Normalized email (trimmed and lowercased)
        """
        return email.strip().lower()
    
    def _paginate_slack_api_call(
        self,
        api_method: Callable,
        result_key: str,
        operation_name: str,
        payload: Optional[Dict[str, Any]] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Generic pagination helper for Slack API calls that support cursor-based pagination.
        
        Args:
            api_method: Slack API method to call (e.g., self.slack_client.client.users_list)
            result_key: Key in the response containing the list of results (e.g., "members")
            operation_name: Human-readable operation name for logging
            payload: Optional base payload to include in each request
            limit: Number of results per page (default: 200)
            
        Returns:
            List of all results from all pages
        """
        results: List[Dict[str, Any]] = []
        cursor = None
        page = 1
        base_payload = payload or {}
        
        while True:
            try:
                page_payload = {**base_payload, "limit": limit}
                if cursor:
                    page_payload["cursor"] = cursor
                
                response = self.slack_client._execute_slack_api_call(
                    api_method=api_method,
                    payload=page_payload,
                    operation_name=f"{operation_name} (page {page})"
                )
                
                if not response.get("success"):
                    logger.error(f"Slack API error: {response.get('error')}")
                    break
                
                api_response = response.get("response", {})
                page_results = api_response.get(result_key, [])
                results.extend(page_results)
                
                cursor = api_response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
                
                page += 1
                    
            except Exception as e:
                logger.error(f"Error during {operation_name} (page {page}): {e}")
                break
        
        return results
    
    def list_all_users(self) -> List[Dict[str, Any]]:
        """
        List all Slack users with pagination and smart retry logic.
        
        Uses SlackClient's _execute_slack_api_call for exponential backoff
        and transient error retry. Fails fast for non-transient errors.
        
        Returns:
            List of all user objects
        """
        return self._paginate_slack_api_call(
            api_method=self.slack_client.client.users_list,
            result_key="members",
            operation_name="Fetch users"
        )
    
    def find_candidates_by_last_name(self, last_name: str) -> List[SlackUser]:
        """
        Find Slack users by last name.
        
        Fetches all users and filters by last name match.
        
        Args:
            last_name: Last name to search for (case-insensitive)
            
        Returns:
            List of SlackUser models matching the last name
        """
        lname = (last_name or "").strip().lower()
        if not lname:
            return []
        
        users = self.list_all_users()
        candidates: List[SlackUser] = []
        
        for user_dict in users:
            try:
                user = SlackUser(**user_dict)
                profile = user_dict.get("profile", {})
                real_name = (
                    profile.get("real_name_normalized") or 
                    profile.get("real_name") or 
                    user_dict.get("name") or 
                    ""
                ).lower()
                
                if lname and (real_name.endswith(" " + lname) or real_name.split()[-1] == lname or lname in real_name):
                    candidates.append(user)
            except Exception as e:
                logger.debug(f"Could not parse user {user_dict.get('id')}: {e}")
                continue
        
        return candidates
    
    def lookup_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Look up a Slack user by email address.
        
        Normalizes the email and uses SlackClient for the actual API call.
        
        Args:
            email: Email address to look up (will be normalized)
            
        Returns:
            Full user object if found, None otherwise
        """
        normalized_email = self.normalize_email(email)
        logger.debug(f"Looking up user by email: {normalized_email}")
        
        try:
            response = self.slack_client._execute_slack_api_call(
                api_method=self.slack_client.client.users_lookupByEmail,
                payload={"email": normalized_email},
                operation_name=f"Lookup user by email: {normalized_email}"
            )
            
            if response.get("success"):
                user = response.get("response", {}).get("user")
                if user:
                    logger.debug(f"✓ Found user: {user.get('id')}")
                    return user
            
            logger.debug(f"✗ No user found for {normalized_email}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to lookup {normalized_email}: {e}")
            return None
    
    def lookup_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Look up a Slack user by user ID.
        
        Validates the user ID format before performing the lookup.
        
        Args:
            user_id: Slack user ID (e.g., U03LZKQSHEU)
            
        Returns:
            Full user object if found, None otherwise
            
        Raises:
            ValueError: If user_id format is invalid
        """
        # Validate user ID format
        if not SlackUser.is_valid_user_id(user_id):
            raise ValueError(
                f"Invalid Slack user ID format: '{user_id}'. "
                f"Must start with 'U', be 11 characters, and contain only alphanumeric characters."
            )
        
        logger.debug(f"Looking up user by ID: {user_id}")
        
        try:
            users = self.list_all_users()
            for user in users:
                if user.get('id') == user_id:
                    logger.debug(f"✓ Found user: {user_id}")
                    return user
            
            logger.debug(f"✗ No user found for {user_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to lookup {user_id}: {e}")
            return None
    
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
        Look up a single email address and return only the user ID.
        
        Used internally for batch lookups. Normalizes email before lookup.
        
        Note: The underlying lookup_user_by_email() already has retry logic via SlackClient.
        The max_retries parameter is unused but kept for backward compatibility.
        
        Args:
            email: Email address to look up (will be normalized)
            max_retries: Unused (kept for backward compatibility)
            
        Returns:
            Slack user ID if found, None otherwise
        """
        try:
            user = self.lookup_user_by_email(email)
            if user:
                return user.get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to lookup {email}: {e}")
            return None

