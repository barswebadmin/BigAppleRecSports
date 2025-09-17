import os
from dotenv import load_dotenv

# Always load .env file, but command line environment variables will override
load_dotenv('../.env', override=False)


class Config:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "dev").lower()

        # Environment-specific Shopify configuration
        if self.environment in ["staging", "production"]:
            # Use production Shopify credentials for staging and production
            self.shopify_store = os.getenv("SHOPIFY_STORE")
            self.shopify_token = os.getenv("SHOPIFY_TOKEN")
            self.shopify_location_id = os.getenv("SHOPIFY_LOCATION_ID")
            self.shopify_rest_url = os.getenv("SHOPIFY_REST_URL")
            self.shopify_admin_url = os.getenv("SHOPIFY_ADMIN_URL")
        else:
            # Use dev/test Shopify credentials (if any) or fallback to production
            self.shopify_store = os.getenv(
                "SHOPIFY_DEV_STORE",
                "SHOPIFY_DEV_STORE"
            )
            self.shopify_token = os.getenv(
                "SHOPIFY_DEV_TOKEN", "SHOPIFY_DEV_TOKEN"
            )
            self.shopify_location_id = os.getenv(
                "SHOPIFY_DEV_LOCATION_ID", "SHOPIFY_DEV_LOCATION_ID"
            )
            self.shopify_rest_url = os.getenv(
                "SHOPIFY_DEV_REST_URL", "SHOPIFY_DEV_REST_URL"
            )
            self.shopify_admin_url = os.getenv(
                "SHOPIFY_DEV_ADMIN_URL", 
                os.getenv("SHOPIFY_ADMIN_URL")
            )


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



config = Config()
