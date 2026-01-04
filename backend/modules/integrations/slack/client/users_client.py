from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from slack_sdk import WebClient

logger = logging.getLogger(__name__)


class SlackUsersClient:
    def __init__(self, bearer_token: str):
        self.client = WebClient(token=bearer_token)

    def list_all_users(self) -> List[Dict[str, Any]]:
        users: List[Dict[str, Any]] = []
        cursor = None
        
        while True:
            try:
                response = self.client.users_list(limit=200, cursor=cursor)
                
                if not response["ok"]:
                    logger.error(f"Slack API error: {response.get('error')}")
                    break
                
                members = response.get("members", [])
                users.extend(members)
                
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching users: {e}")
                break
        
        return users

    @staticmethod
    def find_candidates_by_last_name(users: List[Dict[str, Any]], last_name: str) -> List[Dict[str, Any]]:
        lname = (last_name or "").strip().lower()
        if not lname:
            return []
        candidates: List[Dict[str, Any]] = []
        for u in users:
            profile = u.get("profile", {})
            real_name = (profile.get("real_name_normalized") or profile.get("real_name") or u.get("name") or "").lower()
            if lname and (real_name.endswith(" " + lname) or real_name.split()[-1] == lname or lname in real_name):
                candidates.append(u)
        return candidates
    
    def lookup_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Look up a Slack user by their email address.
        Note: Slack's API is case-insensitive, but we normalize to lowercase for consistency.
        
        Args:
            email: Email address to look up
            
        Returns:
            User object if found, None otherwise
        """
        try:
            response = self.client.users_lookupByEmail(email=email.strip().lower())
            
            if response["ok"]:
                return response.get("user")
                
        except Exception as e:
            logger.error(f"Error looking up user by email {email}: {e}")
        
        return None

