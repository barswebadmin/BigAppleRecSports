"""
Self-contained Slack configuration system.
Loads all Slack-specific configuration independently from main config.
Uses PascalCase for class names and attribute names for enum-like constants.
"""

import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SlackConfig:
    """
    Self-contained Slack configuration system.
    Loads all Slack settings independently from main application config.
    """

    def __init__(self, ENVIRONMENT: str):
        # Honor the environment provided by the main Config, do not re-read os.getenv here
        self.environment = (ENVIRONMENT or "dev").lower()
        logger.info(f"🌍 SlackConfig Environment (from Config): {self.environment}")

    @staticmethod
    def get_environment() -> str:
        return os.getenv("ENVIRONMENT", "dev").lower()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    # --------------------
    # Bots
    # --------------------
    class Bots:
        """
        Usage:
            SlackConfig.Bots.Refunds.token
            SlackConfig.Bots.Registrations.signing_secret
        """

        class _Bot:
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

        Dev               = _Bot("SLACK_BOT_TOKEN_DEV",               "SLACK_SIGNING_SECRET_DEV")
        Exec              = _Bot("SLACK_BOT_TOKEN_EXEC",              "SLACK_SIGNING_SECRET_EXEC")
        Leadership        = _Bot("SLACK_BOT_TOKEN_LEADERSHIP",        "SLACK_SIGNING_SECRET_LEADERSHIP", "SLACK_BOT_USER_TOKEN_LEADERSHIP")
        PaymentAssistance = _Bot("SLACK_BOT_TOKEN_PAYMENT_ASSISTANCE","SLACK_SIGNING_SECRET_PAYMENT_ASSISTANCE")
        Refunds           = _Bot("SLACK_BOT_TOKEN_REFUNDS",           "SLACK_SIGNING_SECRET_REFUNDS")
        Registrations     = _Bot("SLACK_BOT_TOKEN_REGISTRATIONS",     "SLACK_SIGNING_SECRET_REGISTRATIONS")
        Web               = _Bot("SLACK_BOT_TOKEN_WEB",               "SLACK_SIGNING_SECRET_WEB")

    # --------------------
    # Channels
    # --------------------
    class Channels:
        """Slack Channel IDs and friendly names (no leading '#')."""

        class _Channel:
            def __init__(self, channel_id: str, name: str):
                self._id = channel_id
                self._name = name

            @property
            def id(self) -> str:
                return self._id

            @property
            def name(self) -> str:
                return self._name

            def __str__(self):
                return self._id

        JoeTest             = _Channel("C092RU7R6PL", "#joe-test")
        Registrations       = _Channel("C08J1EN7SFR", "#registrations")
        RegistrationRefunds = _Channel("C08J1EN7SFR", "#registration-refunds")
        Web                 = _Channel("C02KAENF6",   "#web")

        @classmethod
        def all(cls) -> Dict[str, _Channel]:
            """Return {friendly_name: {id, name}}."""
            return {
                "joe-test": cls.JoeTest,
                "registrations": cls.Registrations,
                "registration-refunds": cls.RegistrationRefunds,
                "web": cls.Web,
            }

    # --------------------
    # Users
    # --------------------
    class Users:
        """Slack user mentions; expose .mention and .name."""
        class _User:
            def __init__(self, id: str, name: str):
                self.id = id        # e.g., "<@U0278M72535>" or "@here"
                self.name = name              # e.g., "joe" or "here"

            def __str__(self) -> str:
                return self.id

        Joe  = _User("<@U0278M72535>", "joe")
        Here = _User("@here",           "here")

        @classmethod
        def all(cls) -> Dict[str, Dict[str, str]]:
            """Return {PascalName: {'id': mention, 'name': friendly_name}}."""
            out: Dict[str, Dict[str, str]] = {}
            for k, v in cls.__dict__.items():
                if isinstance(v, cls._User):
                    out[k] = {"id": v.id, "name": f"@{v.name}"}
            return out

    
    # --------------------
    # Groups (subteams)
    # --------------------
    # Import from new location to maintain backward compatibility
    from modules.integrations.slack.models.slack_group import Groups as _Groups
    Groups = _Groups


    # Public nested types so external code can annotate reliably
    class Channel(Channels._Channel):
        pass

    class User(Users._User):
        pass

    class Bot(Bots._Bot):
        pass

    class Group(_Groups._Group):
        pass


# Convenience aliases for cleaner imports (container classes, not inner types)
SlackChannel = SlackConfig.Channels
SlackUser    = SlackConfig.Users
SlackGroup   = SlackConfig.Groups
SlackBot     = SlackConfig.Bots
Slack        = SlackConfig  # Main access point