"""Consolidated Slack Bolt app initialization for all bots."""

import os
from typing import Optional, Dict, Any, Union, List
from slack_bolt import App
from modules.integrations.slack.client import SlackClient, SlackUserIdentifier
from modules.integrations.slack.user_lookup import lookup_user as _lookup_user
from modules.integrations.slack.slack_service import SlackService


class BotConfig:
    """Proxy that lazily reads env vars at access time."""
    def __init__(self, token_env: str, secret_env: str, user_token_env: Optional[str] = None):
        self._token_env_name = token_env
        self._secret_env_name = secret_env
        self._user_token_env_name = user_token_env

    @property
    def token(self) -> str:
        v = os.getenv(self._token_env_name)
        if not v:
            raise RuntimeError(f"Missing env: {self._token_env_name}")
        return v

    @property
    def user_token(self) -> Optional[str]:
        """Optional User Token for operations requiring User Token Scopes."""
        if not self._user_token_env_name:
            return None
        return os.getenv(self._user_token_env_name)

    @property
    def signing_secret(self) -> str:
        v = os.getenv(self._secret_env_name)
        if not v:
            raise RuntimeError(f"Missing env: {self._secret_env_name}")
        return v


class Bots:
    """
    Slack Bot configurations.
    
    Usage:
        Bots.Dev.token
        Bots.Leadership.signing_secret
    """
    Dev               = BotConfig("SLACK_BOT_TOKEN_DEV",               "SLACK_SIGNING_SECRET_DEV")
    Exec              = BotConfig("SLACK_BOT_TOKEN_EXEC",              "SLACK_SIGNING_SECRET_EXEC")
    Leadership        = BotConfig("SLACK_BOT_TOKEN_LEADERSHIP",        "SLACK_SIGNING_SECRET_LEADERSHIP", "SLACK_BOT_USER_TOKEN_LEADERSHIP")
    PaymentAssistance = BotConfig("SLACK_BOT_TOKEN_PAYMENT_ASSISTANCE","SLACK_SIGNING_SECRET_PAYMENT_ASSISTANCE")
    Refunds           = BotConfig("SLACK_BOT_TOKEN_REFUNDS",           "SLACK_SIGNING_SECRET_REFUNDS")
    Registrations     = BotConfig("SLACK_BOT_TOKEN_REGISTRATIONS",     "SLACK_SIGNING_SECRET_REGISTRATIONS")
    Web               = BotConfig("SLACK_BOT_TOKEN_WEB",               "SLACK_SIGNING_SECRET_WEB")


class SlackBot(App):
    """
    Slack Bolt App with delegated SlackClient methods and SlackService integration.
    
    Uses Python's __getattr__ to automatically delegate any missing method/attribute
    calls to the underlying client. This leverages Bolt's built-in `client` property
    to provide direct access like:
    - bot.send_message() instead of bot.client.send_message()
    
    Each bot instance has access to:
    - self.client: SlackClient instance
    - self.service: SlackService instance
    - self.token: Bot token
    - self.signing_secret: Signing secret
    - self.user_token: Optional user token
    """
    
    def __init__(
        self,
        bot_config: BotConfig,
        token_verification_enabled: bool = False
    ):
        """
        Initialize SlackBot with bot configuration.
        
        Args:
            bot_config: BotConfig instance with token, signing_secret, and optional user_token
            token_verification_enabled: Whether to enable token verification (default: False for CLI usage)
        """
        # Store bot configuration
        self.bot_config = bot_config
        self.token = bot_config.token
        self.signing_secret = bot_config.signing_secret
        self.user_token = bot_config.user_token
        
        # Initialize SlackClient
        slack_client = SlackClient(
            token=self.token,
            user_token=self.user_token
        )
        
        # Initialize SlackService
        self.service = SlackService()
        
        # Initialize Bolt App with client and signing secret
        super().__init__(
            client=slack_client,
            signing_secret=self.signing_secret,
            token_verification_enabled=token_verification_enabled
        )
    
    @classmethod
    def create(
        cls,
        bot_config: BotConfig,
        token_verification_enabled: bool = False
    ) -> 'SlackBot':
        """
        Factory method to create a SlackBot instance.
        
        Args:
            bot_config: BotConfig instance
            token_verification_enabled: Whether to enable token verification
            
        Returns:
            SlackBot instance
        """
        return cls(bot_config=bot_config, token_verification_enabled=token_verification_enabled)
    
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
            user = bot.lookup_user("user@example.com")
            
            # By user ID
            user = bot.lookup_user("U1234567890")
            
            # With SlackUserIdentifier
            user = bot.lookup_user(SlackUserIdentifier(email="user@example.com"))
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
            channel = bot.lookup_channel("general")
            channel = bot.lookup_channel("#kickball-leadership")
            
            # By ID
            channel = bot.lookup_channel("C092RU7R6PL")
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
        include_archived: bool = False,
        include_private: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all channels visible to the bot.
        
        Args:
            include_archived: If True, include archived channels
            include_private: If True, include private channels (requires appropriate scopes)
            
        Returns:
            List of channel dicts
            
        Note: Admin/Exec bots typically have access to both public and private channels.
        """
        channels = []
        cursor = None
        
        channel_types = "public_channel"
        if include_private:
            channel_types = "public_channel,private_channel"
        
        while True:
            try:
                response = self.client.conversations_list(
                    types=channel_types,
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
    
    def lookup_group(
        self,
        identifier: str
    ) -> Optional[Dict[str, Any]]:
        """
        Look up a Slack usergroup by handle or ID.
        
        Args:
            identifier: Group handle (with or without @) or group ID (e.g., 'S03LZKQSHEU')
            
        Returns:
            Group dict if found, None otherwise
            
        Examples:
            # By handle
            group = bot.lookup_group("leadership")
            group = bot.lookup_group("@leadership")
            
            # By ID
            group = bot.lookup_group("S03LZKQSHEU")
        """
        from modules.integrations.slack.services import UsergroupService
        
        service = UsergroupService(self.client)
        
        # Check if it's a valid group ID (starts with S, 11 chars, alphanumeric)
        if identifier.startswith('S') and len(identifier) == 11 and identifier.isalnum():
            # Lookup by ID
            return service.get_group_by_id(identifier)
        else:
            # Lookup by handle - remove @ if present
            handle = identifier.lstrip('@')
            return service.get_group_by_handle(handle)
    
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


# ============================================================================
# Bot Instance Exports
# ============================================================================

dev_bot = SlackBot.create(
    bot_config=Bots.Dev,
    token_verification_enabled=False
)

exec_bot = SlackBot.create(
    bot_config=Bots.Exec,
    token_verification_enabled=False
)

leadership_bot = SlackBot.create(
    bot_config=Bots.Leadership,
    token_verification_enabled=False
)

payment_assistance_bot = SlackBot.create(
    bot_config=Bots.PaymentAssistance,
    token_verification_enabled=False
)

refunds_bot = SlackBot.create(
    bot_config=Bots.Refunds,
    token_verification_enabled=False
)

registrations_bot = SlackBot.create(
    bot_config=Bots.Registrations,
    token_verification_enabled=False
)

web_bot = SlackBot.create(
    bot_config=Bots.Web,
    token_verification_enabled=False
)

# Alias for admin bot (uses Exec bot which has admin privileges)
admin_bot = exec_bot
