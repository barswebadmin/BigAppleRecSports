import os
from dotenv import load_dotenv

# Only load .env in development
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

class Settings:
    def __init__(self):
        self.shopify_store = os.getenv("SHOPIFY_STORE", "09fe59-3.myshopify.com")
        self.shopify_token = os.getenv("SHOPIFY_TOKEN")
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # CORS settings
        self.allowed_origins = [
            "https://docs.google.com",  # Google Apps Script
            "https://script.google.com",  # Google Apps Script
            "https://barsbackend.onrender.com",  # Production domain
            "http://localhost:8000",  # Local development
            "http://127.0.0.1:8000",  # Local development
        ] if self.environment == "production" else ["*"]
        
        # Only require token in production, allow test tokens for CI
        if not self.shopify_token and self.environment == "production":
            raise ValueError("SHOPIFY_TOKEN environment variable is required")
    
    @property
    def graphql_url(self):
        return f"https://{self.shopify_store}/admin/api/2025-01/graphql.json"

settings = Settings() 