"""Pure functions for Slack user lookups and enrichment.

This is the single source of truth for all Slack user-related operations:
- User lookups (by email, ID, or identifier)
- User listing and searching
- Leadership hierarchy enrichment with Slack user IDs
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Union, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel
from slack_sdk import WebClient

if TYPE_CHECKING:
    from modules.leadership.domain.models import LeadershipHierarchy

from modules.integrations.slack.client import SlackUserIdentifier, UserLookupByEmailPayload
from modules.integrations.slack.models.slack_user import SlackUser

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    """
    Normalize email address for consistent lookups.
    
    Args:
        email: Raw email address
        
    Returns:
        Normalized email (trimmed and lowercased)
    """
    return email.strip().lower()


def _call_slack_api(
    client: WebClient,
    api_method: Callable,
    payload: Union[Dict[str, Any], BaseModel],
    operation_name: str
) -> Dict[str, Any]:
    """
    Call a Slack API method with optional enhanced error handling.
    
    If client is a SlackClient (has _execute_slack_api_call), uses it for better
    error handling and retry logic. Otherwise calls the method directly.
    
    Args:
        client: WebClient instance (SlackClient is a subclass, so it works too)
        api_method: The Slack SDK method to call (e.g., client.users_lookupByEmail)
        payload: Payload as dict or Pydantic model
        operation_name: Human-readable operation name for logging
        
    Returns:
        Dict with 'success', 'response', and optional 'error' keys
    """
    # Convert payload to dict if it's a BaseModel
    if isinstance(payload, BaseModel):
        api_payload = payload.model_dump(exclude_none=True)
    elif isinstance(payload, dict):
        api_payload = payload
    else:
        raise TypeError(f"Payload must be a dict or BaseModel, got {type(payload)}")
    
    # If client has _execute_slack_api_call (SlackClient), use it for better error handling
    execute_method = getattr(client, '_execute_slack_api_call', None)
    if execute_method is not None:
        return execute_method(
            api_method=api_method,
            payload=api_payload,
            operation_name=operation_name
        )
    
    # Otherwise, call the method directly (WebClient)
    try:
        response = api_method(**api_payload)
        if response.get("ok"):
            logger.info(f"✅ {operation_name}")
            return {
                "success": True,
                "response": response
            }
        return {
            "success": False,
            "error": response.get("error", "Unknown error"),
            "response": response
        }
    except Exception as e:
        logger.error(f"❌ {operation_name} failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "response": None
        }


def _paginate_slack_api_call(
    client: WebClient,
    api_method: Callable,
    result_key: str,
    operation_name: str,
    payload: Union[Dict[str, Any], BaseModel],
    limit: int = 200
) -> List[Dict[str, Any]]:
    """
    Generic pagination helper for Slack API calls that support cursor-based pagination.
    
    Works with any payload type (dict or Pydantic model). Automatically merges
    `limit` and `cursor` parameters into the payload for each page.
    
    Args:
        client: WebClient instance (SlackClient is a subclass, so it works too)
        api_method: Slack API method to call (e.g., client.users_list)
        result_key: Key in the response containing the list of results (e.g., "members")
        operation_name: Human-readable operation name for logging
        payload: Base payload (dict or BaseModel) to include in each request.
                 The `limit` and `cursor` parameters will be merged into this payload.
        limit: Number of results per page (default: 200)
        
    Returns:
        List of all results from all pages
        
    Example:
        # With dict payload
        _paginate_slack_api_call(
            client, client.users_list, "members", "Fetch users",
            payload={"include_locale": True}, limit=100
        )
        
        # With Pydantic model payload
        _paginate_slack_api_call(
            client, client.conversations_list, "channels", "Fetch channels",
            payload=ConversationsListPayload(types="public_channel,private_channel")
        )
        
        # With empty dict payload
        _paginate_slack_api_call(
            client, client.users_list, "members", "Fetch users",
            payload={}
        )
    """
    results: List[Dict[str, Any]] = []
    cursor = None
    page = 1
    
    # Convert base payload to dict if it's a BaseModel
    if isinstance(payload, BaseModel):
        # Convert Pydantic model to dict, excluding None values
        base_payload_dict = payload.model_dump(exclude_none=True)
    elif isinstance(payload, dict):
        # Already a dict, use as-is
        base_payload_dict = payload.copy()
    else:
        raise TypeError(f"Payload must be a dict or BaseModel, got {type(payload)}")
    
    while True:
        try:
            # Merge pagination parameters into the base payload
            page_payload = {**base_payload_dict, "limit": limit}
            if cursor:
                page_payload["cursor"] = cursor
            
            response = _call_slack_api(
                client=client,
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


def list_all_users(client: WebClient) -> List[Dict[str, Any]]:
    """
    List all Slack users with pagination and smart retry logic.
    
    Args:
        client: WebClient instance (SlackClient is a subclass, so it works too)
        
    Returns:
        List of all user objects
    """
    return _paginate_slack_api_call(
        client=client,
        api_method=client.users_list,
        result_key="members",
        operation_name="Fetch users",
        payload={}
    )


def find_candidates_by_last_name(client: WebClient, last_name: str) -> List[SlackUser]:
    """
    Find Slack users by last name.
    
    Args:
        client: WebClient instance (SlackClient is a subclass, so it works too)
        last_name: Last name to search for (case-insensitive)
        
    Returns:
        List of SlackUser models matching the last name
    """
    lname = (last_name or "").strip().lower()
    if not lname:
        return []
    
    users = list_all_users(client)
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


def lookup_user(client: WebClient, identifier: SlackUserIdentifier) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack user by email or user ID.
    
    Args:
        client: WebClient instance (SlackClient is a subclass, so it works too)
        identifier: SlackUserIdentifier with either email or user_id
        
    Returns:
        Full user object if found, None otherwise
        
    Raises:
        ValueError: If user_id format is invalid
    """
    if identifier.email:
        return lookup_user_by_email(client, identifier.email)
    
    elif identifier.user_id:
        # Use lookup_user_by_id for direct API call
        return lookup_user_by_id(client, identifier.user_id)
    
    else:
        raise ValueError("SlackUserIdentifier must have either email or user_id")


def lookup_user_by_email(client: WebClient, email: str) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack user by email address using the users.lookupByEmail API.
    
    Args:
        client: WebClient instance (SlackClient is a subclass, so it works too)
        email: Email address to look up (will be normalized)
        
    Returns:
        Full user object if found, None otherwise
    """
    normalized_email = normalize_email(email)
    logger.debug(f"Looking up user by email: {normalized_email}")
    
    try:
        payload = UserLookupByEmailPayload(email=normalized_email)
        response = _call_slack_api(
            client=client,
            api_method=client.users_lookupByEmail,
            payload=payload,
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


def lookup_user_by_id(client: WebClient, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack user by user ID using the users.info API.
    
    Args:
        client: WebClient instance (SlackClient is a subclass, so it works too)
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
        # Use users.info API directly (more efficient than listing all users)
        response = _call_slack_api(
            client=client,
            api_method=client.users_info,
            payload={"user": user_id},
            operation_name=f"Lookup user by ID: {user_id}"
        )
        
        if response.get("success"):
            user = response.get("response", {}).get("user")
            if user:
                logger.debug(f"✓ Found user: {user_id}")
                return user
        
        logger.debug(f"✗ No user found for {user_id}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to lookup {user_id}: {e}")
        return None


def lookup_user_ids_by_emails(
    client: WebClient,
    emails: List[str], 
    max_workers: int = 10
) -> Dict[str, Optional[str]]:
    """
    Look up Slack user IDs for multiple email addresses concurrently.
    
    Args:
        client: WebClient instance (SlackClient is a subclass, so it works too)
        emails: List of email addresses to look up
        max_workers: Maximum number of concurrent API requests (default: 10)
        
    Returns:
        Dictionary mapping email to user ID (or None if not found)
        Example: {"john@example.com": "U12345ABC", "notfound@example.com": None}
    """
    results: Dict[str, Optional[str]] = {}
    
    if not emails:
        return results
    
    logger.info(f"Looking up {len(emails)} email(s) with {max_workers} concurrent workers")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_email = {
            executor.submit(lookup_user_by_email, client, email): email
            for email in emails
        }
        
        for future in as_completed(future_to_email):
            email = future_to_email[future]
            try:
                user = future.result()
                user_id = user.get("id") if user else None
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


def enrich_hierarchy(
    client: WebClient,
    hierarchy: "LeadershipHierarchy",
    max_workers: int = 10
) -> Dict[str, Optional[str]]:
    """
    Enrich a leadership hierarchy with Slack user IDs.
    
    Args:
        client: WebClient instance (SlackClient is a subclass, so it works too)
        hierarchy: The hierarchy to enrich (modified in-place)
        max_workers: Maximum concurrent API requests
        
    Returns:
        Dictionary mapping email -> slack_user_id (or None if not found)
    """
    
    emails = hierarchy.get_all_emails()
    
    if not emails:
        logger.warning("No emails found in hierarchy to enrich")
        return {}
    
    logger.info(f"Enriching hierarchy with {len(emails)} emails")
    
    # Look up all Slack user IDs
    results = lookup_user_ids_by_emails(
        client=client,
        emails=emails,
        max_workers=max_workers
    )
    
    # Add slack_user_id to hierarchy
    _add_slack_ids_to_hierarchy(hierarchy, results)
    
    found_count = sum(1 for uid in results.values() if uid)
    logger.info(f"Enrichment complete: {found_count}/{len(emails)} Slack user IDs found")
    
    return results


def _add_slack_ids_to_hierarchy(
    hierarchy: "LeadershipHierarchy", 
    results: Dict[str, Optional[str]]
) -> None:
    """
    Add slack_user_id field to each person in the hierarchy.
    
    Args:
        hierarchy: The hierarchy to modify (modified in-place)
        results: Dict of email -> slack_user_id from lookup service
    """
    hierarchy_dict = hierarchy.to_dict()
    
    for section_key, section_data in hierarchy_dict.items():
        if section_key == "vacant_positions":
            continue
        
        # Handle simple list sections (like committee_members)
        if isinstance(section_data, list):
            for person in section_data:
                if person and isinstance(person, dict):
                    bars_email = person.get("bars_email", "").strip()
                    if bars_email:
                        person["slack_user_id"] = results.get(bars_email)
            continue
        
        if not isinstance(section_data, dict):
            continue
        
        # Recursively process nested structures
        _enrich_nested_dict(section_data, results)


def _enrich_nested_dict(
    data: Dict, 
    results: Dict[str, Optional[str]]
) -> None:
    """
    Recursively enrich a nested dictionary with Slack user IDs.
    
    Args:
        data: Dictionary to enrich (modified in-place)
        results: Dict of email -> slack_user_id from lookup service
    """
    for key, value in data.items():
        if isinstance(value, dict):
            # Check if this is a person dict (has bars_email)
            if "bars_email" in value:
                bars_email = value.get("bars_email", "").strip()
                if bars_email:
                    value["slack_user_id"] = results.get(bars_email)
            else:
                # Recurse into nested dict
                _enrich_nested_dict(value, results)
        elif isinstance(value, list):
            # Handle lists of people
            for item in value:
                if isinstance(item, dict):
                    if "bars_email" in item:
                        bars_email = item.get("bars_email", "").strip()
                        if bars_email:
                            item["slack_user_id"] = results.get(bars_email)
                    else:
                        _enrich_nested_dict(item, results)

