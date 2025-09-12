import os
from dotenv import load_dotenv

# Only load .env in development
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()


class Settings:
    def __init__(self):
        self.shopify_store = os.getenv("SHOPIFY_STORE", "09fe59-3.myshopify.com")
        self.shopify_token = os.getenv("SHOPIFY_TOKEN")
        self.shopify_location_id = os.getenv("SHOPIFY_LOCATION_ID")
        self.slack_refunds_bot_token = os.getenv("SLACK_REFUNDS_BOT_TOKEN")
        self.slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")
        self.environment = os.getenv("ENVIRONMENT", "production")

        # Slack channels configuration
        self.slack_channels = {
            "refund-requests": {
                "channelId": "C08J1EN7SFR",
                "name": "#registration-refunds",
            },
            "joe-test": {"channelId": "C092RU7R6PL", "name": "#joe-test"},
        }

        # Slack subgroups configuration
        self.slack_subgroups = {
            "kickball": "<!subteam^S08L2521XAM>",
            "bowling": "<!subteam^S08KJJ02738>",
            "pickleball": "<!subteam^S08KTJ33Z9R>",
            "dodgeball": "<!subteam^S08KJJ5CL4W>",
        }

        # Slack users configuration
        self.slack_users = {"joe": "<@U0278M72535>", "here": "@here"}

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

        # Only require token in production, allow test tokens for CI
        if not self.shopify_token and self.environment == "production":
            raise ValueError("SHOPIFY_TOKEN environment variable is required")

        # Debug: Log environment information in CI
        if os.getenv("CI"):
            print(f"[DEBUG] Environment: {self.environment}")
            print(f"[DEBUG] SHOPIFY_TOKEN present: {bool(self.shopify_token)}")
            print(f"[DEBUG] ENVIRONMENT env var: {os.getenv('ENVIRONMENT')}")

    @property
    def graphql_url(self):
        return f"https://{self.shopify_store}/admin/api/2025-01/graphql.json"

    @property
    def is_debug_mode(self) -> bool:
        """
        Determine if we're in debug mode based on ENVIRONMENT.
        Debug mode: mocks API calls, includes debug prefixes in messages
        Production mode: makes real API calls
        """
        return self.environment.lower() in ["development", "debug", "test"]

    @property
    def is_production_mode(self) -> bool:
        """
        Determine if we're in production mode based on ENVIRONMENT.
        Production mode: makes real API calls, no debug prefixes
        """
        return self.environment.lower() == "production"


settings = Settings()
