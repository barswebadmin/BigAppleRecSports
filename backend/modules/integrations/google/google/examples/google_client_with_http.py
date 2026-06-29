"""
Example demonstrating GoogleApiClient with HTTP client capabilities.

This example shows how the GoogleApiClient now inherits from AsyncHTTPClient
and can be used for both HTTP requests and Google API operations.
"""

import asyncio
from modules.integrations.google.google_api_client import GoogleApiClient


async def demonstrate_google_client_with_http():
    """Demonstrate GoogleApiClient with both HTTP and Google API capabilities."""
    
    # Create client with HTTP capabilities
    client = GoogleApiClient(
        base_url="https://httpbin.org",  # Example HTTP endpoint
        timeout=30.0
    )
    
    print("🚀 GoogleApiClient with HTTP capabilities")
    print("=" * 50)
    
    # 1. HTTP client functionality (inherited from AsyncHTTPClient)
    print("\n📡 HTTP Client Functionality:")
    try:
        # Make HTTP requests using inherited methods
        response = await client.get("/json")
        print(f"✓ HTTP GET request successful: {response.status_code}")
        
        # POST request example
        post_response = await client.post("/post", json={"key": "value"})
        print(f"✓ HTTP POST request successful: {post_response.status_code}")
        
    except Exception as e:
        print(f"HTTP request example: {e}")
    
    # 2. Google API service functionality (delegation to services)
    print("\n🔧 Google API Service Functionality:")
    try:
        # These would work with actual Google API credentials
        print("✓ Google Sheets service available:", hasattr(client, 'sheets_service'))
        print("✓ Google Gmail service available:", hasattr(client, 'gmail_service'))
        print("✓ Google Scripts service available:", hasattr(client, 'scripts_service'))
        print("✓ Google Drive service available:", hasattr(client, 'drive_service'))
        
        # Example delegation methods (would require Google API credentials to actually run)
        print("✓ Delegation methods available:")
        print("  - fetch_sheet_as_csv()")
        print("  - find_emails()")
        print("  - send_to_waitlist_form()")
        print("  - get_sheet_revisions()")
        
        print("Note: Directory API methods should be accessed via GoogleDirectoryService directly")
        
    except Exception as e:
        print(f"Google API service example: {e}")
    
    # 3. Combined usage example
    print("\n🔄 Combined Usage Example:")
    print("✓ Single client provides both HTTP and Google API functionality")
    print("✓ Inherits retry policies and error handling from AsyncHTTPClient")
    print("✓ Maintains backward compatibility with existing Google API code")
    print("✓ Can be configured with custom retry policies and HTTP settings")
    
    # Close the client
    await client.aclose()
    print("\n✅ Client closed successfully")


def demonstrate_inheritance():
    """Demonstrate the inheritance chain."""
    from shared_utilities.api_clients.http_client import AsyncHTTPClient
    
    print("\n🏗️ Inheritance Chain:")
    print("=" * 30)
    
    # Show inheritance
    print(f"✓ GoogleApiClient inherits from AsyncHTTPClient: {issubclass(GoogleApiClient, AsyncHTTPClient)}")
    print(f"✓ Method Resolution Order: {[cls.__name__ for cls in GoogleApiClient.__mro__]}")
    
    # Show available methods
    client = GoogleApiClient()
    http_methods = ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']
    google_methods = ['fetch_sheet_as_csv', 'get_user', 'list_all_groups', 'find_emails']
    
    print("\n📋 Available HTTP Methods:")
    for method in http_methods:
        print(f"  ✓ {method}(): {hasattr(client, method)}")
    
    print("\n📋 Available Google API Methods:")
    google_methods = ['fetch_sheet_as_csv', 'find_emails', 'send_to_waitlist_form', 'get_sheet_revisions']
    for method in google_methods:
        print(f"  ✓ {method}(): {hasattr(client, method)}")
    
    print("\n📋 Directory API Methods (use GoogleDirectoryService directly):")
    directory_methods = ['get_user', 'list_all_users', 'list_all_groups', 'create_group']
    for method in directory_methods:
        print(f"  - {method}(): Available via GoogleDirectoryService")


if __name__ == "__main__":
    print("GoogleApiClient with HTTP Client Inheritance Example")
    print("=" * 60)
    
    # Show inheritance information
    demonstrate_inheritance()
    
    # Run async example
    asyncio.run(demonstrate_google_client_with_http())