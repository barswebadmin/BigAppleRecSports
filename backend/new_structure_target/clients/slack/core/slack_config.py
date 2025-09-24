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
        self.environment = os.getenv("ENVIRONMENT", "dev").lower()
        logger.info(f"🌍 SlackConfig Environment: {self.environment}")

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
            def __init__(self, token_env: str, secret_env: str):
                self._token_env_name = token_env
                self._secret_env_name = secret_env

            @property
            def token(self) -> str:
                v = os.getenv(self._token_env_name)
                if not v:
                    raise RuntimeError(f"Missing env: {self._token_env_name}")
                return v

            @property
            def signing_secret(self) -> str:
                v = os.getenv(self._secret_env_name)
                if not v:
                    raise RuntimeError(f"Missing env: {self._secret_env_name}")
                return v

        Dev               = _Bot("SLACK_BOT_TOKEN_DEV",               "SLACK_SIGNING_SECRET_DEV")
        Exec              = _Bot("SLACK_BOT_TOKEN_EXEC",              "SLACK_SIGNING_SECRET_EXEC")
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
    class Groups:
        """Slack User Groups (subteams), accessible by PascalCase attributes only."""

        class _Group:
            def __init__(self, id: str, name: str):
                self.id = id
                self.name = name

            def __str__(self) -> str:
                return self.id

        # Top-level
        Kickball   = _Group("<!subteam^S08L2521XAM>", "kickball")
        Bowling    = _Group("<!subteam^S08KJJ02738>", "bowling")
        Pickleball = _Group("<!subteam^S08KTJ33Z9R>", "pickleball")
        Dodgeball  = _Group("<!subteam^S08KJJ5CL4W>", "dodgeball")

        # Bowling
        BowlingMonday = _Group("<!subteam^S09FKLZGP7X>", "bowling-monday")
        BowlingSunday = _Group("<!subteam^S09F7G2B0VD>", "bowling-sunday")

        # Dodgeball
        DodgeballWtnbSocial       = _Group("<!subteam^S09FKLN0SBX>", "dodgeball-wtnb-social")
        DodgeballWtnbDraft        = _Group("<!subteam^S09GFAVQ41E>", "dodgeball-wtnb-draft")
        DodgeballBigBall           = _Group("<!subteam^S09FHSR9ZNF>", "dodgeball-bigball")
        DodgeballSmallBallSocial  = _Group("<!subteam^S09FMV42FGA>", "dodgeball-smallball-social")
        DodgeballSmallBallAdvanced = _Group("<!subteam^S09FKKU1U4D>", "dodgeball-smallball-advanced")
        DodgeballFoamBall         = _Group("<!subteam^S09GFD2D67J>", "dodgeball-foamball")

        # Kickball
        KickballMonday      = _Group("<!subteam^S09FN0P7UTC>", "kickball-monday")
        KickballTuesday     = _Group("<!subteam^S09FSNWKTKN>", "kickball-tuesday")
        KickballWednesday   = _Group("<!subteam^S09G205V0JD>", "kickball-wednesday")
        KickballWtnbThursday= _Group("<!subteam^S09FN0WGZKL>", "kickball-wtnb-thursday")
        KickballWtnbSocial  = _Group("<!subteam^S09FKLYHB2R>", "kickball-wtnb-social")
        KickballThursday    = _Group("<!subteam^S09G22N4SG1>", "kickball-thursday")
        KickballSaturday    = _Group("<!subteam^S09G21RM22D>", "kickball-saturday")
        KickballSunday      = _Group("<!subteam^S09FSNVD5EY>", "kickball-sunday")

        # Pickleball
        PickleballTuesdaySocial   = _Group("<!subteam^S09G20K6LM7>", "pickleball-tuesday-social")
        PickleballTuesdayAdvanced = _Group("<!subteam^S09G20K6LM7>", "pickleball-tuesday-advanced")  # same ID per source
        PickleballThursday        = _Group("<!subteam^S09F7GCF91D>", "pickleball-thursday")
        PickleballSundayWtnb      = _Group("<!subteam^S09FKM2JA9K>", "pickleball-sunday-wtnb")

        @classmethod
        def all(cls) -> dict[str, dict[str, str]]:
            """Return all groups as {PascalCaseName: {'id': mention, 'name': '#friendly'}}"""
            out = {}
            for k, v in cls.__dict__.items():
                if isinstance(v, cls._Group):
                    out[k] = {"id": v.id, "name": f"#{v.name}"}
            return out

        @classmethod
        def get(cls, key: str) -> Dict[str, str]:
            """
            Lookup by PascalCase attribute name (e.g., 'Dodgeball')
            or by lowercase friendly name (e.g., 'dodgeball').
            Returns {'id': mention, 'name': '#friendly'}.
            """
            # Try PascalCase attribute
            if hasattr(cls, key):
                v = getattr(cls, key)
                if isinstance(v, cls._Group):
                    return {"id": v.id, "name": f"#{v.name}"}

            # Try lowercase friendly
            for v in cls.__dict__.values():
                if isinstance(v, cls._Group) and v.name.lower() == key.lower():
                    return {"id": v.id, "name": f"#{v.name}"}

            return {"id": "@here", "name": "@here"}


    # Public nested types so external code can annotate reliably
    class Channel(Channels._Channel):
        pass

    class User(Users._User):
        pass

    class Bot(Bots._Bot):
        pass

    class Group(Groups._Group):
        pass


# Convenience aliases for cleaner imports (container classes, not inner types)
SlackChannel = SlackConfig.Channels
SlackUser    = SlackConfig.Users
SlackGroup   = SlackConfig.Groups
SlackBot     = SlackConfig.Bots
Slack        = SlackConfig  # Main access point