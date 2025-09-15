import os
from dotenv import load_dotenv

# Only load .env in development
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()


class Settings:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "dev").lower()

        # Environment-specific Shopify configuration
        if self.environment in ["staging", "production"]:
            # Use production Shopify credentials for staging and production
            self.shopify_store = os.getenv("SHOPIFY_STORE", "09fe59-3.myshopify.com")
            self.shopify_token = os.getenv("SHOPIFY_TOKEN")
            self.shopify_location_id = os.getenv("SHOPIFY_LOCATION_ID")
            self.shopify_rest_url = os.getenv("SHOPIFY_REST_URL")
        else:
            # Use dev/test Shopify credentials (if any) or fallback to production
            self.shopify_store = os.getenv(
                "SHOPIFY_DEV_STORE",
                os.getenv("SHOPIFY_STORE", "09fe59-3.myshopify.com"),
            )
            self.shopify_token = os.getenv(
                "SHOPIFY_DEV_TOKEN", os.getenv("SHOPIFY_TOKEN")
            )
            self.shopify_location_id = os.getenv(
                "SHOPIFY_DEV_LOCATION_ID", os.getenv("SHOPIFY_LOCATION_ID")
            )
            self.shopify_rest_url = os.getenv(
                "SHOPIFY_DEV_REST_URL", os.getenv("SHOPIFY_REST_URL")
            )

        # Slack configuration (environment-aware)
        self.slack_refunds_bot_token = os.getenv("SLACK_REFUNDS_BOT_TOKEN")
        self.slack_dev_bot_token = os.getenv("SLACK_DEV_BOT_TOKEN")
        self.slack_dev_signing_secret = os.getenv("SLACK_DEV_SIGNING_SECRET")
        self.slack_signing_secret = os.getenv("SLACK_SIGNING_SECRET")

        # Slack channels configuration
        self.slack_channels = {
            "refund-requests": {
                "channelId": "C08J1EN7SFR",
                "name": "#registration-refunds",
            },
            "joe-test": {"channelId": "C092RU7R6PL", "name": "#joe-test"},
        }

        # AWS Lambda URLs for scheduling
        self.aws_schedule_product_changes_url = os.getenv(
            "AWS_SCHEDULE_PRODUCT_CHANGES_URL"
        )
        self.aws_payment_assistance_url = os.getenv("AWS_PAYMENT_ASSISTANCE_URL")

        # Generic AWS endpoint (fallback)
        self.aws_create_product_endpoint = os.getenv("AWS_CREATE_PRODUCT_ENDPOINT")

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

        # Token validation based on environment
        if self.environment in ["staging", "production"] and not self.shopify_token:
            raise ValueError(
                "SHOPIFY_TOKEN environment variable is required for staging/production"
            )
        elif self.environment in ["dev", "test"] and not self.shopify_token:
            print(
                f"[INFO] No SHOPIFY_TOKEN provided for {self.environment} environment - will use mocks"
            )

        # Debug: Log environment information in CI
        if os.getenv("CI"):
            print(f"[DEBUG] Environment: {self.environment}")
            print(f"[DEBUG] SHOPIFY_TOKEN present: {bool(self.shopify_token)}")
            print(f"[DEBUG] ENVIRONMENT env var: {os.getenv('ENVIRONMENT')}")

    @property
    def graphql_url(self):
        return f"https://{self.shopify_store}/admin/api/2025-07/graphql.json"

    @property
    def rest_url(self):
        return (
            self.shopify_rest_url or f"https://{self.shopify_store}/admin/api/2025-07"
        )

    @property
    def is_production_mode(self) -> bool:
        """
        Determine if we're in production mode based on ENVIRONMENT.
        Production mode: makes real API calls, no debug prefixes
        """
        return self.environment.lower() == "production"

    @property
    def active_slack_bot_token(self) -> str:
        """
        Return the appropriate Slack bot token based on environment.
        - Production: uses SLACK_REFUNDS_BOT_TOKEN
        - Non-production: uses SLACK_DEV_BOT_TOKEN if available, otherwise falls back to production token
        """
        if self.is_production_mode:
            return self.slack_refunds_bot_token or ""
        else:
            # Use dev token if available, otherwise fallback to production token
            return self.slack_dev_bot_token or self.slack_refunds_bot_token or ""

    @property
    def active_slack_signing_secret(self) -> str:
        """
        Return the appropriate Slack signing secret based on environment.
        - Production: uses SLACK_SIGNING_SECRET
        - Non-production: uses SLACK_DEV_SIGNING_SECRET if available, otherwise falls back to production secret
        """
        if self.is_production_mode:
            return self.slack_signing_secret or ""
        else:
            # Use dev signing secret if available, otherwise fallback to production secret
            return self.slack_dev_signing_secret or self.slack_signing_secret or ""


settings = Settings()
