"""Pure functions for Slack user lookups.

Single source of truth for all Slack user-related lookup operations.
No backend dependencies — safe to use in Lambda and shared_utilities.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel
from slack_sdk import WebClient

from shared_utilities.clients.slack.client import SlackUserIdentifier, UserLookupByEmailPayload
from shared_utilities.clients.slack.models.slack_user import SlackUser

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _call_slack_api(
    client: WebClient,
    api_method: Callable,
    payload: Union[Dict[str, Any], BaseModel],
    operation_name: str,
) -> Dict[str, Any]:
    if isinstance(payload, BaseModel):
        api_payload = payload.model_dump(exclude_none=True)
    elif isinstance(payload, dict):
        api_payload = payload
    else:
        raise TypeError(f"Payload must be a dict or BaseModel, got {type(payload)}")

    execute = getattr(client, "_execute_slack_api_call", None)
    if execute is not None:
        return execute(api_method=api_method, payload=api_payload, operation_name=operation_name)

    try:
        response = api_method(**api_payload)
        if response.get("ok"):
            logger.info("✅ %s", operation_name)
            return {"success": True, "response": response}
        return {"success": False, "error": response.get("error", "Unknown error"), "response": response}
    except Exception as e:
        logger.error("❌ %s failed: %s", operation_name, str(e))
        return {"success": False, "error": str(e), "response": None}


def _paginate_slack_api_call(
    client: WebClient,
    api_method: Callable,
    result_key: str,
    operation_name: str,
    payload: Union[Dict[str, Any], BaseModel],
    limit: int = 200,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    cursor = None
    page = 1

    base: Dict[str, Any] = payload.model_dump(exclude_none=True) if isinstance(payload, BaseModel) else dict(payload)

    while True:
        try:
            page_payload = {**base, "limit": limit}
            if cursor:
                page_payload["cursor"] = cursor

            response = _call_slack_api(client, api_method, page_payload, f"{operation_name} (page {page})")
            if not response.get("success"):
                logger.error("Slack API error: %s", response.get("error"))
                break

            api_response = response.get("response", {})
            results.extend(api_response.get(result_key, []))
            cursor = api_response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
            page += 1
        except Exception as e:
            logger.error("Error during %s (page %d): %s", operation_name, page, e)
            break

    return results


def list_all_users(client: WebClient) -> List[Dict[str, Any]]:
    return _paginate_slack_api_call(client, client.users_list, "members", "Fetch users", {})


def find_candidates_by_last_name(client: WebClient, last_name: str) -> List[SlackUser]:
    lname = (last_name or "").strip().lower()
    if not lname:
        return []
    candidates: List[SlackUser] = []
    for user_dict in list_all_users(client):
        try:
            user = SlackUser(**user_dict)
            profile = user_dict.get("profile", {})
            real_name = (
                profile.get("real_name_normalized") or profile.get("real_name") or user_dict.get("name") or ""
            ).lower()
            if real_name.endswith(" " + lname) or real_name.split()[-1] == lname or lname in real_name:
                candidates.append(user)
        except Exception as e:
            logger.debug("Could not parse user %s: %s", user_dict.get("id"), e)
    return candidates


def lookup_user(client: WebClient, identifier: SlackUserIdentifier) -> Optional[Dict[str, Any]]:
    if identifier.email:
        return lookup_user_by_email(client, identifier.email)
    if identifier.user_id:
        return lookup_user_by_id(client, identifier.user_id)
    raise ValueError("SlackUserIdentifier must have either email or user_id")


def lookup_user_by_email(client: WebClient, email: str) -> Optional[Dict[str, Any]]:
    normalized = normalize_email(email)
    try:
        payload = UserLookupByEmailPayload(email=normalized)
        response = _call_slack_api(client, client.users_lookupByEmail, payload, f"Lookup user by email: {normalized}")
        if response.get("success"):
            user = response.get("response", {}).get("user")
            if user:
                return user
        return None
    except Exception as e:
        logger.error("Failed to lookup %s: %s", normalized, e)
        return None


def lookup_user_by_id(client: WebClient, user_id: str) -> Optional[Dict[str, Any]]:
    if not SlackUser.is_valid_user_id(user_id):
        raise ValueError(f"Invalid Slack user ID format: '{user_id}'")
    try:
        response = _call_slack_api(client, client.users_info, {"user": user_id}, f"Lookup user by ID: {user_id}")
        if response.get("success"):
            return response.get("response", {}).get("user")
        return None
    except Exception as e:
        logger.error("Failed to lookup %s: %s", user_id, e)
        return None


def lookup_user_ids_by_emails(
    client: WebClient,
    emails: List[str],
    max_workers: int = 10,
) -> Dict[str, Optional[str]]:
    results: Dict[str, Optional[str]] = {}
    if not emails:
        return results
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_email = {executor.submit(lookup_user_by_email, client, email): email for email in emails}
        for future in as_completed(future_to_email):
            email = future_to_email[future]
            try:
                user = future.result()
                results[email] = user.get("id") if user else None
            except Exception as e:
                logger.error("Unexpected error looking up %s: %s", email, e)
                results[email] = None
    return results
