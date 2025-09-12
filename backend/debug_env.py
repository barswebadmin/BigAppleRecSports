#!/usr/bin/env python3
"""
Quick debug script to check environment variables in Render
Add this as a temporary route to see what Render is actually using
"""

from fastapi import APIRouter
import os
from config import settings

router = APIRouter()


@router.get("/debug/env")
async def debug_environment():
    """DEBUG ONLY - Remove after debugging"""
    return {
        "environment": os.getenv("ENVIRONMENT", "not_set"),
        "shopify_store": settings.shopify_store,
        "shopify_token_prefix": settings.shopify_token[:15] + "..."
        if settings.shopify_token
        else "not_set",
        "graphql_url": settings.graphql_url,
        "all_env_vars": {
            k: v[:15] + "..."
            if k.upper().endswith("TOKEN") or k.upper().endswith("SECRET")
            else v
            for k, v in os.environ.items()
            if "SHOPIFY" in k.upper()
            or "SLACK" in k.upper()
            or k.upper() == "ENVIRONMENT"
        },
    }
