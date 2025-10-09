from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from typing import Any
import logging

from .slack import SlackConfig as SlackConfig
from .shopify import ShopifyConfig as ShopifyConfig

logger = logging.getLogger(__name__)

# Always load .env file, but command line environment variables will override
# Try multiple possible .env file locations
env_paths = [
    find_dotenv('../../.env'),  # From backend/config/
    find_dotenv('.env'),        # From project root
    '.env'                      # Direct path
]
for env_path in env_paths:
    if env_path and os.path.exists(env_path):
        load_dotenv(env_path, override=False)
        break

# Get environment - NO DEFAULT VALUE
env_value = os.getenv("ENVIRONMENT")
if not env_value:
    raise RuntimeError("Missing env: ENVIRONMENT")
default_env = env_value.lower()

class Config:
    def __init__(self, ENVIRONMENT: str = default_env):
        self.environment = ENVIRONMENT.lower()
        logger.info(f"🌍 MAIN CONFIG Environment: {self.environment}")
        self.slack = SlackConfig(self.environment)
        self.shopify = ShopifyConfig(self.environment)

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
                "https://bars-backend.onrender.com",  # Production domain
                "http://localhost:8000",  # Local development
                "http://127.0.0.1:8000",  # Local development
            ]
            if self.environment == "production"
            else ["*"]
        )

    @staticmethod
    def get_env() -> str:
        return os.getenv("ENVIRONMENT").lower()

    @property
    def Slack(self):
        return self.slack
    
    @property
    def Shopify(self):
        return self.shopify
    

    



config = Config()

# Slack = config.Slack
# Shopify = config.Shopify
