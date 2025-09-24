import os
from dotenv import load_dotenv
from new_structure_target.clients.slack.core.slack_config import SlackConfig as _SlackConfig
from new_structure_target.clients.shopify.core.shopify_config import ShopifyConfig as _ShopifyConfig
import logging
logger = logging.getLogger(__name__)

# Always load .env file, but command line environment variables will override
load_dotenv('../.env', override=False)


class Config:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "dev").lower()
        logger.info(f"🌍 MAIN CONFIG Environment: {self.environment}")
        # Expose SlackConfig under concise aliases for app usage
        self.Slack = _SlackConfig(self.environment)
        self.SlackBot = self.Slack.Bots
        self.SlackChannel = self.Slack.Channels
        self.SlackUser = self.Slack.Users
        self.SlackGroup = self.Slack.Groups
        # Shopify
        self.Shopify = _ShopifyConfig(self.environment)

        # AWS Lambda URLs for scheduling
        self.aws_schedule_product_changes_url = os.getenv(
            "AWS_SCHEDULE_PRODUCT_CHANGES_URL"
        )
        self.aws_payment_assistance_url = os.getenv("AWS_PAYMENT_ASSISTANCE_URL")

        # Generic AWS endpoint (fallback)
        self.aws_create_product_endpoint = os.getenv("AWS_CREATE_PRODUCT_ENDPOINT")


        # CORS settings
        self.allowed_origins = (
            [
                "https://docs.google.com",  # Google Apps Script
                "https://script.google.com",  # Google Apps Script
                "https://barsbackend.onrender.com",  # Production domain
                "http://localhost:8000",  # Local development
                "http://127.0.0.1:8000",  # Local development
            ]
            if self.environment == "production"
            else ["*"]
        )

    @property
    def is_production(self) -> bool:
        """
        Determine if we're in production mode based on ENVIRONMENT.
        Production mode: makes real API calls, no debug prefixes
        """
        return "prod" in self.environment.lower()
    

    



config = Config()
# Backwards-compat alias expected by CI/scripts
settings = config

Slack = config.Slack
SlackBot = config.SlackBot
SlackChannel = config.SlackChannel
SlackUser = config.SlackUser
SlackGroup = config.SlackGroup
Shopify = config.Shopify

# Re-export SlackConfig as a concrete class with explicit nested type aliases
class SlackConfig(_SlackConfig):
    Channel = _SlackConfig.Channel
    Bot = _SlackConfig.Bot
    User = _SlackConfig.User
    Group = _SlackConfig.Group
