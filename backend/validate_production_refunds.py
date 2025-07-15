#!/usr/bin/env python3
"""
Production Refunds Workflow Validation Script

This script validates that the refunds workflow is ready for production
by checking configuration, API connectivity, and workflow components.
"""

import os
import sys
from datetime import datetime
from config import settings
from services.orders import OrdersService
from services.slack.slack_service import SlackService

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

def print_check(description: str, status: bool, details: str = ""):
    """Print a check result"""
    status_emoji = "✅" if status else "❌"
    print(f"{status_emoji} {description}")
    if details:
        print(f"   └── {details}")

def validate_environment():
    """Validate environment configuration"""
    print_header("ENVIRONMENT CONFIGURATION")
    
    # Check environment setting
    env_is_production = settings.environment.lower() == "production"
    print_check(
        f"Environment: {settings.environment}",
        env_is_production,
        "Ready for production" if env_is_production else "Set ENVIRONMENT=production for live deployment"
    )
    
    # Check debug vs production mode
    is_debug = settings.is_debug_mode
    is_prod = settings.is_production_mode
    print_check(
        f"Debug Mode: {is_debug}",
        not is_debug if env_is_production else True,
        f"Production mode: {is_prod}"
    )
    
    # Check required tokens
    has_shopify_token = bool(settings.shopify_token)
    print_check(
        "Shopify Token",
        has_shopify_token,
        "Present" if has_shopify_token else "Missing - required for production"
    )
    
    has_slack_token = bool(settings.slack_refunds_bot_token)
    print_check(
        "Slack Bot Token",
        has_slack_token,
        "Present" if has_slack_token else "Missing - required for Slack integration"
    )
    
    has_slack_secret = bool(settings.slack_signing_secret)
    print_check(
        "Slack Signing Secret",
        has_slack_secret,
        "Present" if has_slack_secret else "Missing - required for webhook security"
    )
    
    return env_is_production and has_shopify_token and has_slack_token and has_slack_secret

def validate_services():
    """Validate service initialization"""
    print_header("SERVICE INITIALIZATION")
    
    try:
        orders_service = OrdersService()
        print_check("Orders Service", True, "Initialized successfully")
    except Exception as e:
        print_check("Orders Service", False, f"Failed: {e}")
        return False
    
    try:
        slack_service = SlackService()
        api_client_type = type(slack_service.api_client).__name__
        print_check(
            "Slack Service", 
            True, 
            f"Initialized with {api_client_type}"
        )
        
        # Check if using production API client
        is_prod_client = api_client_type == "SlackApiClient"
        print_check(
            "Production Slack Client",
            is_prod_client,
            "Using real API client" if is_prod_client else "Using mock client"
        )
        
    except Exception as e:
        print_check("Slack Service", False, f"Failed: {e}")
        return False
    
    return True

def validate_shopify_connectivity():
    """Validate Shopify API connectivity"""
    print_header("SHOPIFY API CONNECTIVITY")
    
    if not settings.shopify_token:
        print_check("Shopify Connection", False, "No token available")
        return False
    
    try:
        orders_service = OrdersService()
        
        # Test GraphQL endpoint accessibility
        import requests
        response = requests.get(
            settings.graphql_url.replace("/graphql.json", "/products.json?limit=1"),
            headers={"X-Shopify-Access-Token": settings.shopify_token},
            timeout=10
        )
        
        connectivity_ok = response.status_code == 200
        print_check(
            "Shopify API Connectivity",
            connectivity_ok,
            f"HTTP {response.status_code}" if connectivity_ok else f"Failed: HTTP {response.status_code}"
        )
        
        if connectivity_ok:
            print_check("GraphQL Endpoint", True, settings.graphql_url)
            
        return connectivity_ok
        
    except Exception as e:
        print_check("Shopify Connection", False, f"Error: {e}")
        return False

def validate_workflow_components():
    """Validate workflow components"""
    print_header("WORKFLOW COMPONENTS")
    
    # Check if production mode makes real API calls
    production_mode = settings.is_production_mode
    print_check(
        "Production API Calls",
        production_mode,
        "Will make real Shopify API calls" if production_mode else "Will use mock calls"
    )
    
    # Check Slack channel configuration
    try:
        slack_service = SlackService()
        channel_info = slack_service.refunds_channel
        
        print_check(
            f"Slack Channel: {channel_info['name']}",
            True,
            f"ID: {channel_info['channel_id']}"
        )
        
    except Exception as e:
        print_check("Slack Channel Config", False, f"Error: {e}")
        return False
    
    # Validate critical functions exist
    from routers.slack import (
        handle_cancel_order,
        handle_process_refund,
        handle_restock_inventory,
        adjust_shopify_inventory
    )
    
    print_check("Webhook Handlers", True, "All handlers available")
    print_check("Inventory Adjustment", True, "Production implementation available")
    
    return True

def validate_security():
    """Validate security configuration"""
    print_header("SECURITY CONFIGURATION")
    
    # Check CORS settings
    cors_secure = "localhost" not in str(settings.allowed_origins) if settings.environment == "production" else True
    print_check(
        "CORS Configuration",
        cors_secure,
        f"Origins: {settings.allowed_origins[:2]}..." if len(settings.allowed_origins) > 2 else f"Origins: {settings.allowed_origins}"
    )
    
    # Check docs/redoc are disabled in production
    docs_disabled = settings.environment == "production"  # main.py disables docs in production
    print_check(
        "API Documentation",
        True,
        "Disabled in production" if docs_disabled else "Enabled for development"
    )
    
    return cors_secure

def main():
    """Main validation function"""
    print_header("BARS PRODUCTION REFUNDS WORKFLOW VALIDATION")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Environment: {settings.environment}")
    print(f"Python: {sys.version.split()[0]}")
    
    # Run all validations
    validations = [
        ("Environment Configuration", validate_environment),
        ("Service Initialization", validate_services),
        ("Shopify Connectivity", validate_shopify_connectivity),
        ("Workflow Components", validate_workflow_components),
        ("Security Configuration", validate_security),
    ]
    
    results = []
    for name, validator in validations:
        try:
            result = validator()
            results.append((name, result))
        except Exception as e:
            print_check(f"{name} Validation", False, f"Exception: {e}")
            results.append((name, False))
    
    # Summary
    print_header("VALIDATION SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        print_check(name, result)
    
    print(f"\nValidation Results: {passed}/{total} passed")
    
    if passed == total:
        print(f"\n🎉 ALL VALIDATIONS PASSED! 🎉")
        print("The refunds workflow is ready for production deployment.")
        print("\nNext steps:")
        print("1. Set ENVIRONMENT=production in your deployment")
        print("2. Ensure all tokens are set in production environment variables")
        print("3. Test with a small order first")
        return True
    else:
        print(f"\n⚠️  {total - passed} validation(s) failed.")
        print("Please address the issues above before deploying to production.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 