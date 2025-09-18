import os
from dotenv import load_dotenv
from new_structure_target.clients.slack.core.slack_config import SlackConfig as _SlackConfig
from new_structure_target.clients.shopify.core.shopify_config import ShopifyConfig as _ShopifyConfig

# Always load .env file, but command line environment variables will override
load_dotenv('../.env', override=False)


class Config:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "dev").lower()
        # Expose SlackConfig under concise aliases for app usage
        self.Slack = _SlackConfig(self.environment)
        self.SlackBot = _SlackConfig.Bots
        self.SlackChannel = _SlackConfig.Channels
        self.SlackUser = _SlackConfig.Users
        self.SlackGroup = _SlackConfig.Groups
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
