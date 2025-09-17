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
        
        
        @staticmethod
        def get_group_mention(name: str) -> Optional[str]:
            """Dynamically get group mention by name."""
            name = name.lower()
            group_mapping = {
                "bowling": SlackConfig.Group.Bowling,
                "dodgeball": SlackConfig.Group.Dodgeball,
                "kickball": SlackConfig.Group.Kickball,
                "pickleball": SlackConfig.Group.Pickleball,

                "bowling-monday": SlackConfig.Group.BowlingMonday,
                "bowling-sunday": SlackConfig.Group.BowlingSunday,

                "dodgeball-big-ball": SlackConfig.Group.DodgeballMonday,
                "dodgeball-smallball-social": SlackConfig.Group.DodgeballSmallBallSocial,
                "dodgeball-wtnb-draft": SlackConfig.Group.DodgeballWtnbDraft,
                "dodgeball-foam ball": SlackConfig.Group.DodgeballFoamBall,
                "dodgeball-smallball-advanced": SlackConfig.Group.DodgeballSmallBallAdvanced,
                "dodgeball-wtnb-social": SlackConfig.Group.DodgeballWtnbSocial,
                
                "kickball-monday": SlackConfig.Group.KickballMonday,
                "kickball-tuesday": SlackConfig.Group.KickballTuesday,
                "kickball-wtnb-social": SlackConfig.Group.KickballWtnbSocial,
                "kickball-thursday": SlackConfig.Group.KickballThursday,
                "kickball-saturday": SlackConfig.Group.KickballSaturday,
                "kickball-wtnb-social": SlackConfig.Group.KickballWtnbSocial,
                "kickball-sunday-kickball": SlackConfig.Group.KickballSunday,
                
                "pickleball-tuesday-advanced": SlackConfig.Group.PickleballTuesdayAdvanced,
                "pickleball-tuesday-social": SlackConfig.Group.PickleballTuesdaySocial,
                "pickleball-thursday": SlackConfig.Group.PickleballThursday,
                "pickleball-sunday-wtnb": SlackConfig.Group.PickleballSundayWtnb,
            }
            return group_mapping.get(name)
        
        @classmethod
        def get_all(cls) -> Dict[str, str]:
            """Get all sport group mappings."""
            return {
                "kickball": cls.Kickball,
                "bowling": cls.Bowling,
                "pickleball": cls.Pickleball,
                "dodgeball": cls.Dodgeball,
            }

    class Token:
        """Slack token management."""
        
        # Bot tokens as static methods (callable like constants)
        @staticmethod
        def RefundsBot() -> Optional[str]:
            """Get the refunds bot token."""
            return os.getenv("SLACK_REFUNDS_BOT_TOKEN")
        
        @staticmethod
        def RegistrationsBot() -> Optional[str]:
            """Get the registrations bot token."""
            return os.getenv("SLACK_REGISTRATIONS_BOT_TOKEN")
        
        @staticmethod
        def DevBot() -> Optional[str]:
            """Get the dev bot token."""
            return os.getenv("SLACK_DEV_BOT_TOKEN")
        
        @staticmethod
        def get_refunds_token() -> Optional[str]:
            """Get the refunds bot token."""
            return os.getenv("SLACK_REFUNDS_BOT_TOKEN")
        
        @staticmethod
        def get_registrations_token() -> Optional[str]:
            """Get the registrations bot token."""
            return os.getenv("SLACK_REGISTRATIONS_BOT_TOKEN")
        
        @staticmethod
        def get_dev_token() -> Optional[str]:
            """Get the dev bot token."""
            return os.getenv("SLACK_DEV_BOT_TOKEN")
        
        @staticmethod
        def resolve_bot_token(bot_name: str) -> Optional[str]:
            """Resolve bot name to token."""
            bot_name = bot_name.lower().replace(' ', '').replace('_', '').replace('-', '')
            
            # Map bot names to token getters
            bot_mapping = {
                'registrations': SlackConfig.Token.get_registrations_token,
                'registrationsbot': SlackConfig.Token.get_registrations_token,
                'refunds': SlackConfig.Token.get_refunds_token,
                'refundsbot': SlackConfig.Token.get_refunds_token,
                'dev': SlackConfig.Token.get_dev_token,
                'devbot': SlackConfig.Token.get_dev_token,
            }
            
            token_getter = bot_mapping.get(bot_name)
            return token_getter() if token_getter else None
        
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