"""Slack Bolt app initialization for Web bot."""

from typing import Optional, Dict, Any, Union, List
from slack_bolt import App
from config.slack import SlackConfig
from modules.integrations.slack.client import SlackClient, SlackUserIdentifier
from modules.integrations.slack.user_lookup import lookup_user as _lookup_user


class WebBot(App):
    """
    Slack Bolt App with delegated SlackClient methods.
    
    Uses Python's __getattr__ to automatically delegate any missing method/attribute
    calls to the underlying client. This leverages Bolt's built-in `client` property
    to provide direct access like:
    - web_bot.send_message() instead of web_bot.client.send_message()
    """
    
    def lookup_user(
        self,
        identifier: Union[str, SlackUserIdentifier]
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a Slack user by email or user ID.
        
        Args:
            identifier: Either a string (email or user_id) or SlackUserIdentifier instance
            
        Returns:
            Full user object if found, None otherwise
            
        Examples:
            # By email
            user = web_bot.lookup_user("user@example.com")
            
            # By user ID
            user = web_bot.lookup_user("U1234567890")
            
            # With SlackUserIdentifier
            user = web_bot.lookup_user(SlackUserIdentifier(email="user@example.com"))
        """
        # Convert string to SlackUserIdentifier if needed
        if isinstance(identifier, str):
            if '@' in identifier:
                identifier = SlackUserIdentifier(email=identifier)
            else:
                identifier = SlackUserIdentifier(user_id=identifier)
        
        # Call the user_lookup function with this bot's client
        return _lookup_user(self.client, identifier)
    
    def lookup_channel(
        self,
        identifier: str
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a Slack channel by name or ID.
        
        Args:
            identifier: Channel name (with or without #) or channel ID (e.g., 'C01ABC123')
            
        Returns:
            Channel dict if found, None otherwise
            
        Examples:
            # By name
            channel = web_bot.lookup_channel("general")
            channel = web_bot.lookup_channel("#kickball-leadership")
            
            # By ID
            channel = web_bot.lookup_channel("C092RU7R6PL")
        """
        from modules.integrations.slack.models.slack_channel import SlackChannel
        
        # Check if it's a valid channel ID
        if SlackChannel.is_valid_channel_id(identifier):
            # Lookup by ID
            try:
                response = self.client.conversations_info(channel=identifier)
                if response.get('ok'):
                    return response.get('channel')
                return None
            except Exception:
                return None
        else:
            # Lookup by name - get all channels and find by name
            channel_name = identifier.lstrip('#').lower()
            channels = self.list_all_channels()
            
            for channel in channels:
                if channel.get('name', '').lower() == channel_name:
                    return channel
            
            return None
    
    def list_all_channels(
        self,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all public channels visible to the bot.
        
        Args:
            include_archived: If True, include archived channels
            
        Returns:
            List of channel dicts
            
        Note: Only lists public channels. Private channels would require 'groups:read' scope.
        """
        channels = []
        cursor = None
        
        while True:
            try:
                response = self.client.conversations_list(
                    types="public_channel",
                    cursor=cursor,
                    limit=200
                )
                
                if response.get('ok'):
                    response_channels = response.get('channels', [])
                    if response_channels:
                        channels.extend(response_channels)
                    cursor = response.get('response_metadata', {}).get('next_cursor')
                    if not cursor:
                        break
                else:
                    break
            except Exception:
                break
        
        # Filter archived channels if requested
        if not include_archived:
            channels = [c for c in channels if not c.get('is_archived', False)]
        
        return channels
    
    def __getattr__(self, name: str):
        """
        Delegate missing attributes/methods to the client.
        
        This is called when an attribute is not found on the App instance.
        We check if the client has it and return it, allowing direct access to
        client methods without going through .client.
        """
        # Use the built-in client property from App
        client = self.client
        
        # Check if client has the attribute
        if hasattr(client, name):
            attr = getattr(client, name)
            # If it's callable, return a bound method
            if callable(attr):
                # Return the method bound to the client
                return attr
            # Otherwise return the attribute value
            return attr
        
        # If not found, raise AttributeError (standard Python behavior)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


web_bot = WebBot(
    client=SlackClient(
        token=SlackConfig.Bots.Web.token
        user_token=SlackConfig.Bots.Web.user_token
    ),
    signing_secret=SlackConfig.Bots.Web.signing_secret,
    token_verification_enabled=False  # Disable token verification for Enterprise Grid tokens and CLI usage
)

