"""
Self-contained Slack configuration system.
Loads all Slack-specific configuration independently from main config.
Uses PascalCase for class names and attribute names for enum-like constants.
"""

import os
from typing import Dict, Any, Optional


class SlackConfig:
    """
    Self-contained Slack configuration system.
    Loads all Slack settings independently from main application config.
    """

    def __init__(self):
        """Initialize Slack configuration from environment variables."""
        self.environment = os.getenv("ENVIRONMENT", "dev").lower()

    @property
    def is_production(self) -> bool:
        """Check if we're in production mode."""
        return self.environment.lower() == "production"


    class Channel:
        """Slack Channel IDs and names."""
        
        # Channel IDs
        JoeTest: str = "C092RU7R6PL"         # #joe-test
        Registrations: str = "C08J1EN7SFR"   # #registrations
        RegistrationRefunds: str = "C08J1EN7SFR"  # #registration-refunds
        Web: str = "C02KAENF6"               # #web
        
        @staticmethod
        def get_channel_id(name: str) -> Optional[str]:
            """Dynamically get channel ID by name."""
            channel_map = {
                "registration-refunds": SlackConfig.Channel.RegistrationRefunds,
                "joe-test": SlackConfig.Channel.JoeTest,
            }
            return channel_map.get(name.lower())
        
        @staticmethod
        def resolve_channel_id(channel: str) -> Optional[str]:
            """Resolve channel name to ID."""
            # If it's already a channel ID (starts with C), return as-is
            if channel.startswith('C'):
                return channel
                
            # Normalize channel name
            channel_name = channel.lower().replace('#', '').replace('_', '-').strip()
            
            # Map channel names to IDs
            channel_mapping = {
                'joe-test': SlackConfig.Channel.JoeTest,
                'joetest': SlackConfig.Channel.JoeTest,
                'registration-refunds': SlackConfig.Channel.RegistrationRefunds,
                'registrationrefunds': SlackConfig.Channel.RegistrationRefunds,
                'refunds': SlackConfig.Channel.RegistrationRefunds,
            }
            
            return channel_mapping.get(channel_name)
        
        @classmethod
        def get_all(cls) -> Dict[str, str]:
            """Get all channel mappings."""
            return {
                "joe-test": cls.JoeTest,
                "registration-refunds": cls.RegistrationRefunds,
                "registrations": cls.Registrations,
                "web": cls.Web,
            }

    class User:
        """Slack User mentions."""
        
        # User mentions
        Joe: str = "<@U0278M72535>"
        Here: str = "@here"
        
        @staticmethod
        def get_user_mention(name: str) -> Optional[str]:
            """Dynamically get user mention by name."""
            name = name.lower()
            user_mapping = {
                "joe": SlackConfig.User.Joe,
                "here": SlackConfig.User.Here,
            }
            return user_mapping.get(name)
        
        @classmethod
        def get_all(cls) -> Dict[str, str]:
            """Get all user mappings."""
            return {
                "joe": cls.Joe,
                "here": cls.Here,
            }

    class Group:
        """Slack Group mentions."""
        
        # Group mentions
        Kickball: str = "<!subteam^S08L2521XAM>"
        Bowling: str = "<!subteam^S08KJJ02738>"
        Pickleball: str = "<!subteam^S08KTJ33Z9R>"
        Dodgeball: str = "<!subteam^S08KJJ5CL4W>"

        # Individual leagues
        BowlingMonday: str = "<!subteam^S09FKLZGP7X>"
        BowlingSunday: str = "<!subteam^S09F7G2B0VD>"

        DodgeballWtnbSocial: str = "<!subteam^S09FKLN0SBX>"
        DodgeballWtnbDraft: str = "<!subteam^S09GFAVQ41E>"
        DodgeballMonday: str = "<!subteam^S09FHSR9ZNF>"
        DodgeballSmallBallSocial: str = "<!subteam^S09FMV42FGA>"
        DodgeballSmallBallAdvanced: str = "<!subteam^S09FKKU1U4D>"
        DodgeballFoamBall: str = "<!subteam^S09GFD2D67J>"

        KickballMonday: str = "<!subteam^S09FN0P7UTC>"
        KickballTuesday: str = "<!subteam^S09FSNWKTKN>"
        KickballWednesday: str = "<!subteam^S09G205V0JD>"
        KickballWtnbThursday: str = "<!subteam^S09FN0WGZKL>"
        KickballWtnbSocial: str = "<!subteam^S09FKLYHB2R>"
        KickballThursday: str = "<!subteam^S09G22N4SG1>"
        KickballSaturday: str = "<!subteam^S09G21RM22D>"
        KickballSunday: str = "<!subteam^S09FSNVD5EY>"

        PickleballTuesdaySocial: str = "<!subteam^S09G20K6LM7>"
        PickleballTuesdayAdvanced: str = "<!subteam^S09G20K6LM7>"
        PickleballThursday: str = "<!subteam^S09F7GCF91D>"
        PickleballSundayWtnb: str = "<!subteam^S09FKM2JA9K>"
        
        @classmethod
        def get_all_group_mappings(cls) -> Dict[str, str]:
            """Get all sport group mappings."""
            return {
                "kickball": cls.Kickball,
                "bowling": cls.Bowling,
                "pickleball": cls.Pickleball,
                "dodgeball": cls.Dodgeball,

                "bowling-monday": cls.BowlingMonday,
                "bowling-sunday": cls.BowlingSunday,

                "dodgeball-big-ball": cls.DodgeballMonday,
                "dodgeball-smallball-social": cls.DodgeballSmallBallSocial,
                "dodgeball-wtnb-draft": cls.DodgeballWtnbDraft,
                "dodgeball-foam ball": cls.DodgeballFoamBall,
                "dodgeball-smallball-advanced": cls.DodgeballSmallBallAdvanced,
                "dodgeball-wtnb-social": cls.DodgeballWtnbSocial,
                
                "kickball-monday": cls.KickballMonday,
                "kickball-tuesday": cls.KickballTuesday,
                "kickball-wtnb-social": cls.KickballWtnbSocial,
                "kickball-thursday": cls.KickballThursday,
                "kickball-saturday": cls.KickballSaturday,
                "kickball-wtnb-social": cls.KickballWtnbSocial,
                "kickball-sunday-kickball": cls.KickballSunday,
                
                "pickleball-tuesday-advanced": cls.PickleballTuesdayAdvanced,
                "pickleball-tuesday-social": cls.PickleballTuesdaySocial,
                "pickleball-thursday": cls.PickleballThursday,
                "pickleball-sunday-wtnb": cls.PickleballSundayWtnb,
            }

    class Token:
        """Slack token management."""

        # Class-level token values (read from environment at import time)
        Exec: Optional[str] = os.getenv("SLACK_EXEC_BOT_TOKEN")
        Refunds: Optional[str] = os.getenv("SLACK_REFUNDS_BOT_TOKEN")
        Registrations: Optional[str] = os.getenv("SLACK_REGISTRATIONS_BOT_TOKEN")
        Dev: Optional[str] = os.getenv("SLACK_DEV_BOT_TOKEN")

        @classmethod
        def get_all(cls) -> Dict[str, Optional[str]]:
            """Get all bot tokens keyed by normalized bot name."""
            return {
                "refunds": cls.Refunds,
                "registrations": cls.Registrations,
                "dev": cls.Dev,
            }
        
        @staticmethod
        def get_signing_secret() -> Optional[str]:
            """Get the active signing secret based on environment."""
            environment = os.getenv("ENVIRONMENT", "dev").lower()
            if environment == "production":
                return os.getenv("SLACK_SIGNING_SECRET")
            else:
                # Use dev signing secret if available, otherwise fallback to production secret
                return os.getenv("SLACK_DEV_SIGNING_SECRET") or os.getenv("SLACK_SIGNING_SECRET")
        
        @staticmethod
        def get_dev_signing_secret() -> Optional[str]:
            """Get the dev signing secret."""
            return os.getenv("SLACK_DEV_SIGNING_SECRET")
        
        @staticmethod
        def get_active_signing_secret() -> Optional[str]:
            """Get the active signing secret based on environment."""
            environment = os.getenv("ENVIRONMENT", "dev").lower()
            if environment == "production":
                return os.getenv("SLACK_SIGNING_SECRET")
            else:
                # Use dev signing secret if available, otherwise fallback to production secret
                return os.getenv("SLACK_DEV_SIGNING_SECRET") or os.getenv("SLACK_SIGNING_SECRET")

    @staticmethod
    def get_environment() -> str:
        """Get the current environment."""
        return os.getenv("ENVIRONMENT", "dev").lower()

    @staticmethod
    def is_production_mode() -> bool:
        """Check if we're in production mode."""
        return os.getenv("ENVIRONMENT", "dev").lower() == "production"

# Convenience aliases for cleaner imports
SlackChannel = SlackConfig.Channel
SlackUser = SlackConfig.User
SlackGroup = SlackConfig.Group
SlackToken = SlackConfig.Token
Slack = SlackConfig  # Main access point