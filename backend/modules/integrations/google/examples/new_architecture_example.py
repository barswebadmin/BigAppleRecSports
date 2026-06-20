#!/usr/bin/env python3
"""
Example demonstrating the new Google API client architecture.

This example shows how to use the refactored Google API client with:
1. Generic service execution with credential caching
2. Service-specific methods using the new client
3. Request models for structured data
"""

import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from modules.integrations.google.google_api_client import GoogleApiClient
from modules.integrations.google.services.google_directory_service import GoogleDirectoryService
from modules.integrations.google.models.requests import GetGroupsRequest, CreateGoogleGroupRequest
from modules.integrations.google.scopes import DirectoryScopes


def example_new_architecture():
    """Demonstrate the new Google API client architecture."""
    
    print("🚀 Google API Client Architecture Example")
    print("=" * 50)
    
    # 1. Initialize the unified client
    print("\n1. Initializing Google API Client...")
    client = GoogleApiClient()
    print("   ✅ Client initialized with credential caching and HTTP capabilities")
    
    # 2. Access scopes with dot notation
    print("\n2. Accessing scopes with dot notation...")
    scopes = DirectoryScopes()
    print(f"   📋 Groups readonly scope: {scopes.groups_readonly}")
    print(f"   📝 Groups readwrite scope: {scopes.groups_readwrite}")
    print(f"   👤 Users readonly scope: {scopes.users_readonly}")
    
    # 3. Create request models
    print("\n3. Creating request models...")
    get_groups_request = GetGroupsRequest(
        customer="my_customer",
        max_results=10
    )
    print(f"   📋 Get groups request: {get_groups_request}")
    
    create_group_request = CreateGoogleGroupRequest(
        email="test-group@bigapplerecsports.com",
        name="Test Group",
        description="A test group for demonstration"
    )
    print(f"   📝 Create group request: {create_group_request}")
    
    # 4. Initialize service with client
    print("\n4. Initializing Directory Service with client...")
    directory_service = GoogleDirectoryService(client=client)
    print("   ✅ Directory service initialized with new client")
    
    # 5. Demonstrate generic API execution (without actually calling Google)
    print("\n5. Generic API execution example...")
    print("   🔧 The client can execute any Google API request with:")
    print("      - service_name: 'admin', 'sheets', 'drive', etc.")
    print("      - version: 'directory_v1', 'v4', etc.")
    print("      - scopes: List of OAuth scopes")
    print("      - resource: 'groups', 'users', etc.")
    print("      - method: 'list', 'get', 'insert', etc.")
    print("      - params: Query parameters")
    print("      - body: Request body for POST/PUT")
    
    # Example of what a call would look like (commented out to avoid actual API calls):
    """
    response = client.execute_request(
        service_name="admin",
        version="directory_v1", 
        scopes=[scopes.groups_readonly],
        resource="groups",
        method="list",
        params={"customer": "my_customer", "maxResults": 10}
    )
    """
    
    # 6. Service-specific methods
    print("\n6. Service-specific methods...")
    print("   📋 directory_service.get_groups(request) - Uses new client architecture")
    print("   👤 directory_service.list_all_users() - Uses legacy service (backward compatibility)")
    print("   🔧 Both approaches work, new architecture provides better caching and error handling")
    
    print("\n🎉 Architecture demonstration complete!")
    print("\nKey Benefits:")
    print("✅ Centralized credential management with caching")
    print("✅ Generic API execution for any Google service")
    print("✅ Service-specific methods for complex operations")
    print("✅ Structured request models with validation")
    print("✅ Backward compatibility with existing code")
    print("✅ HTTP client capabilities for non-Google APIs")


if __name__ == "__main__":
    try:
        example_new_architecture()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)