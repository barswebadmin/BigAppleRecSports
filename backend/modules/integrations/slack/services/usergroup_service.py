"""
Modern Slack Usergroup Service using slack_sdk.

Provides CRUD operations for Slack usergroups (teams/subteams).
Replaces the old usergroup_client.py with modern slack_sdk integration.
"""
from typing import List, Dict, Optional, Any
import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


class UsergroupService:
    """
    Modern Slack usergroup operations using slack_sdk.
    
    Provides individual usergroup operations (list, get, create, update).
    For bulk operations, see UsergroupProvisioner.
    """
    
    def __init__(self, client: WebClient):
        """
        Initialize with slack_sdk WebClient.
        
        Args:
            client: Initialized WebClient with valid bot token
        """
        self.client = client
    
    def list_groups(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        List all usergroups visible to the bot.
        
        Args:
            include_disabled: Whether to include disabled groups
            
        Returns:
            List of usergroup dicts with keys: id, name, handle, user_count, users, etc.
            
        Raises:
            SlackApiError: If API call fails
        """
        try:
            response = self.client.usergroups_list(
                include_count=True,
                include_disabled=include_disabled,
                include_users=True
            )
            
            if not response['ok']:
                logger.error(f"Failed to list usergroups: {response.get('error')}")
                return []
            
            return response.get('usergroups', [])
            
        except SlackApiError as e:
            logger.error(f"Slack API error listing usergroups: {e}")
            raise
    
    def get_group_by_id(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Get usergroup details by ID.
        
        Args:
            group_id: Slack usergroup ID (e.g., 'S03LZKQSHEU')
            
        Returns:
            Usergroup dict or None if not found
            
        Raises:
            SlackApiError: If API call fails (except not_found)
        """
        try:
            response = self.client.usergroups.info(  # type: ignore
                usergroup=group_id,
                include_users=True
            )
            
            if response.get('ok'):
                return response.get('usergroup')
            
            logger.warning(f"Usergroup {group_id} not found")
            return None
            
        except SlackApiError as e:
            if e.response.get('error') == 'usergroup_not_found':
                logger.warning(f"Usergroup {group_id} not found")
                return None
            logger.error(f"Slack API error getting usergroup {group_id}: {e}")
            raise
    
    def get_group_by_handle(self, handle: str) -> Optional[Dict[str, Any]]:
        """
        Get usergroup by handle (e.g., 'leadership', 'dodgeball-monday').
        
        Args:
            handle: Usergroup handle (without @ prefix)
            
        Returns:
            Usergroup dict or None if not found
        """
        groups = self.list_groups(include_disabled=True)
        return next((g for g in groups if g.get('handle') == handle), None)
    
    def create_group(
        self,
        name: str,
        handle: str,
        description: str = "",
        channels: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Create a new usergroup.
        
        Args:
            name: Display name (e.g., "Dodgeball Leadership")
            handle: Handle for mentions (e.g., "dodgeball-monday")
            description: Optional description
            channels: Optional list of default channel IDs
            
        Returns:
            Usergroup ID if successful, None otherwise
            
        Raises:
            SlackApiError: If API call fails
        """
        try:
            kwargs: Dict[str, Any] = {
                'name': name,
                'handle': handle,
            }
            
            if description:
                kwargs['description'] = description
            
            if channels:
                kwargs['channels'] = ','.join(channels)  # Slack expects comma-separated string
            
            response = self.client.usergroups_create(**kwargs)  # type: ignore
            
            if response.get('ok'):
                usergroup = response.get('usergroup')
                if usergroup:
                    group_id = usergroup['id']
                    logger.info(f"Created usergroup '{name}' with ID {group_id}")
                    return group_id
            
            logger.error(f"Failed to create usergroup '{name}': {response.get('error')}")
            return None
            
        except SlackApiError as e:
            logger.error(f"Slack API error creating usergroup '{name}': {e}")
            raise
    
    def update_group_members(
        self,
        group_id: str,
        user_ids: List[str]
    ) -> bool:
        """
        Update usergroup members (REPLACES existing members).
        
        NOTE: Slack's API replaces all members, it does NOT append.
        To add a single user, you must include all existing + new user IDs.
        
        Args:
            group_id: Usergroup ID
            user_ids: List of Slack user IDs to set as members
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            SlackApiError: If API call fails
        """
        try:
            response = self.client.usergroups_users_update(
                usergroup=group_id,
                users=user_ids
            )
            
            if response['ok']:
                logger.info(f"Updated usergroup {group_id} with {len(user_ids)} members")
                return True
            
            logger.error(f"Failed to update usergroup {group_id}: {response.get('error')}")
            return False
            
        except SlackApiError as e:
            logger.error(f"Slack API error updating usergroup {group_id}: {e}")
            raise
    
    def get_group_members(self, group_id: str) -> List[str]:
        """
        Get current member IDs for a usergroup.
        
        Args:
            group_id: Usergroup ID
            
        Returns:
            List of Slack user IDs (empty list if not found)
        """
        group = self.get_group_by_id(group_id)
        return group.get('users', []) if group else []
    
    def add_user_to_group(self, group_id: str, user_id: str) -> bool:
        """
        Add a single user to a usergroup (preserves existing members).
        
        Args:
            group_id: Usergroup ID
            user_id: Slack user ID to add
            
        Returns:
            True if successful, False otherwise
        """
        current_members = self.get_group_members(group_id)
        
        if user_id in current_members:
            logger.info(f"User {user_id} already in group {group_id}")
            return True
        
        new_members = current_members + [user_id]
        return self.update_group_members(group_id, new_members)
    
    def remove_user_from_group(self, group_id: str, user_id: str) -> bool:
        """
        Remove a single user from a usergroup (preserves other members).
        
        Args:
            group_id: Usergroup ID
            user_id: Slack user ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        current_members = self.get_group_members(group_id)
        
        if user_id not in current_members:
            logger.info(f"User {user_id} not in group {group_id}")
            return True
        
        new_members = [uid for uid in current_members if uid != user_id]
        return self.update_group_members(group_id, new_members)
    
    def disable_group(self, group_id: str) -> bool:
        """
        Disable a usergroup.
        
        Args:
            group_id: Usergroup ID
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            SlackApiError: If API call fails
        """
        try:
            response = self.client.usergroups_disable(usergroup=group_id)
            
            if response['ok']:
                logger.info(f"Disabled usergroup {group_id}")
                return True
            
            logger.error(f"Failed to disable usergroup {group_id}: {response.get('error')}")
            return False
            
        except SlackApiError as e:
            logger.error(f"Slack API error disabling usergroup {group_id}: {e}")
            raise
    
    def enable_group(self, group_id: str) -> bool:
        """
        Enable a usergroup.
        
        Args:
            group_id: Usergroup ID
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            SlackApiError: If API call fails
        """
        try:
            response = self.client.usergroups_enable(usergroup=group_id)
            
            if response['ok']:
                logger.info(f"Enabled usergroup {group_id}")
                return True
            
            logger.error(f"Failed to enable usergroup {group_id}: {response.get('error')}")
            return False
            
        except SlackApiError as e:
            logger.error(f"Slack API error enabling usergroup {group_id}: {e}")
            raise

